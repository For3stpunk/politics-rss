#!/usr/bin/env python3
"""
merge_feeds.py

Pulls every RSS feed listed in FEEDS, merges the items by publish date
(newest first), and writes ONE combined feed you can check at a glance.

Outputs three files:
  - combined.xml   a real RSS 2.0 feed (import this into any reader,
                    or point a website widget at it)
  - combined.html  a plain, single-page digest (open it directly in a browser)
  - index.html     same as combined.html, so GitHub Pages serves it at the
                    bare repo URL

Run it manually, or on a schedule via GitHub Actions (see
.github/workflows/update.yml) so combined.xml / combined.html stay current.

Requires: feedparser  (pip install feedparser)

--------------------------------------------------------------------------
A NOTE ON COVERAGE (read this before you run it)
--------------------------------------------------------------------------
This file attempts EVERY outlet from the source list -- about 230 real
publications once you strip out aggregator tools and duplicates. Feed
URLs below were filled in using each site's most common CMS convention
(WordPress "/feed/", Substack "/feed", known outlet-specific paths for
majors like NYT/Guardian/Economist, etc.) rather than verified one by
one -- there are simply too many to hand-check individually.

That means some WILL be wrong or dead on first run: outlets that turned
off public RSS, paywalled feeds, sites that moved CMS, etc. That's fine --
fetch_all() below already catches parse failures per-feed and prints
`[skip] Name: could not parse (...)`, then keeps going. Run the script,
read the console output, and:
  - delete entries that 404 permanently
  - fix the URL for ones that redirect to a working feed elsewhere
  - re-comment entries that are social/video-only and have no article feed

Three categories of entries are deliberately EXCLUDED, not just guessed
badly:
  1. Pure aggregator/curation TOOLS (Feedly, Pocket, Substack.com itself,
     Medium.com itself, Flipboard, RSS.app, Inoreader, Readwise Reader) --
     these are readers, not content sources, so there's nothing to feed
     into a feed. See the "custom feed in Feedly/Inoreader" write-up
     alongside this script for how to use THEM to group everything below.
  2. Confirmed-defunct outlets (The Outline, Input Magazine, The Recount,
     The Offing) -- left out entirely rather than pointing at a dead
     domain. (Bookforum ceased in 2022 but relaunched under The Nation
     in 2023 and is active again, so it IS included below.)
  3. Social/video-native accounts with no article RSS of their own
     (NowThis, AJ+, Valuetainment, Secular Talk, Breaking Points,
     Triggernometry) -- noted in a comment so you can add their YouTube
     channel feed by hand if you want video items in the mix
     (https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxxxx).
"""

import feedparser
import html
from datetime import datetime, timezone
from email.utils import format_datetime

FEEDS = {

    "Left / Progressive / Socialist": {
        "Jacobin": "https://jacobin.com/feed/",
        "Current Affairs": "https://www.currentaffairs.org/rss/",
        "Dissent": "https://www.dissentmagazine.org/feed/",
        "The Nation": "https://www.thenation.com/feed/",
        "Mother Jones": "https://www.motherjones.com/feed/",
        "In These Times": "https://inthesetimes.com/feed",
        "CounterPunch": "https://www.counterpunch.org/feed/",
        "Common Dreams": "https://www.commondreams.org/rss.xml",
        "Truthout": "https://truthout.org/feed/",
        "The Intercept": "https://theintercept.com/feed/",
        "Democracy Now!": "https://www.democracynow.org/democracy_now.rss",
        "The Lever": "https://www.levernews.com/feed",
        "More Perfect Union": "https://perfectunion.us/feed/",
        "Red Pepper": "https://www.redpepper.org.uk/feed/",
        "Tribune": "https://tribunemag.co.uk/feed",
        "Novara Media": "https://novaramedia.com/feed/",
        "Evolve Politics": "https://evolvepolitics.com/feed/",
        "The Canary": "https://www.thecanary.co/feed/",
        "New Left Review": "https://newleftreview.org/feed",
        "Monthly Review": "https://monthlyreview.org/feed/",
    },

    "Liberal / Center-Left": {
        "The Atlantic": "https://www.theatlantic.com/feed/all/",
        "The New Yorker": "https://www.newyorker.com/feed/everything",
        "Vox": "https://www.vox.com/rss/index.xml",
        "Slate": "https://slate.com/feeds/all.rss",
        "Salon": "https://www.salon.com/feed/",
        "The New Republic": "https://newrepublic.com/feed",
        "The Guardian": "https://www.theguardian.com/international/rss",
        "The Independent": "https://www.independent.co.uk/rss",
        "Prospect": "https://www.prospectmagazine.co.uk/feed",
        "Harper's Magazine": "https://harpers.org/feed/",
        "The Economist": "https://www.economist.com/rss",  # verify -- Economist gates most feeds
        "Financial Times": "https://www.ft.com/rss/home",
        "Politico": "https://www.politico.com/rss/politicopicks.xml",
        "Axios": "https://www.axios.com/feed",
        "The Week": "https://theweek.com/feed/all",
    },

    "Center / Nonpartisan / Data-Driven": {
        "Pew Research Center": "https://www.pewresearch.org/feed/",
        "ProPublica": "https://www.propublica.org/feeds/propublica/main",
        "Reuters": "https://feeds.reuters.com/reuters/topNews",  # verify -- Reuters pulled most public feeds
        "Associated Press": "https://apnews.com/rss",  # verify -- AP has no reliable public RSS anymore
        "AllSides": "https://www.allsides.com/rss.xml",
        "RealClearPolitics": "https://www.realclearpolitics.com/index.xml",
        "FiveThirtyEight": "https://fivethirtyeight.com/politics/feed/",  # verify -- archived under ABC News
        "Brookings Institution": "https://www.brookings.edu/feed/",
        "Council on Foreign Relations": "https://www.cfr.org/rss.xml",
        "RAND Corporation": "https://www.rand.org/content/rand/blog.xml",
    },

    "Conservative / Right": {
        "National Review": "https://www.nationalreview.com/feed/",
        "The American Conservative": "https://www.theamericanconservative.com/feed/",
        "The Spectator": "https://www.spectator.co.uk/feed",
        "The Telegraph": "https://www.telegraph.co.uk/rss.xml",
        "Washington Examiner": "https://www.washingtonexaminer.com/feed/",
        "The Federalist": "https://thefederalist.com/feed/",
        "Daily Caller": "https://dailycaller.com/feed/",
        "Breitbart News": "https://www.breitbart.com/feed/",
        "The Blaze": "https://www.theblaze.com/feeds/feed.rss",
        "Commentary Magazine": "https://www.commentary.org/feed/",
    },

    "Libertarian / Cross-Ideological / Hybrid": {
        "Reason": "https://reason.com/feed/",
        "Quillette": "https://quillette.com/feed/",
        "Persuasion": "https://www.persuasion.community/feed",
        "The Dispatch": "https://thedispatch.com/feed/",
        "UnHerd": "https://unherd.com/feed/",
    },

    "Global / Non-U.S.": {
        "Le Monde diplomatique": "https://mondediplo.com/spip.php?page=backend",
        "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
        "EUobserver": "https://euobserver.com/rss.xml",
        "Rest of World": "https://restofworld.org/feed/",
        "The Diplomat": "https://thediplomat.com/feed/",
    },

    "Culture + Politics Hybrid": {
        "n+1": "https://www.nplusonemag.com/feed/",
        "The Baffler": "https://thebaffler.com/feed",
        "Dazed": "https://www.dazeddigital.com/rss",
        "The New Inquiry": "https://thenewinquiry.com/feed/",
        "Public Books": "https://www.publicbooks.org/feed/",
    },

    "Substack / Newsletter Ecosystem": {
        "Platformer": "https://www.platformer.news/feed",
        "Slow Boring": "https://www.slowboring.com/feed",
        "The Free Press": "https://www.thefp.com/feed",
        # "Common Sense with Bari Weiss" is The Free Press's old name -- same feed, skipped as a duplicate.
        "Letters from an American": "https://heathercoxrichardson.substack.com/feed",
    },

    "Academic / Theory Journals": {
        "Political Quarterly": "https://politicalquarterly.org.uk/feed/",  # verify
        "Journal of Democracy": "https://www.journalofdemocracy.org/feed/",  # verify -- may be Project MUSE-gated
        "Foreign Affairs": "https://www.foreignaffairs.com/rss.xml",
        "World Politics Review": "https://www.worldpoliticsreview.com/rss",
        "American Affairs": "https://americanaffairsjournal.org/feed/",
    },

    # Digital-First / Social Media Native: NowThis, AJ+, Valuetainment, and
    # NowThis Politics publish almost entirely to video/social with no
    # article RSS -- add their YouTube channel feed by hand if wanted.
    # The Recount shut down in 2022. Vox Video is covered by the Vox
    # entry above.

    "Investigative / Watchdog": {
        "OpenSecrets": "https://www.opensecrets.org/news/feed/",
        "Center for Investigative Reporting (Reveal)": "https://revealnews.org/feed/",
        "Bellingcat": "https://www.bellingcat.com/feed/",
        "The Marshall Project": "https://www.themarshallproject.org/rss/all.rss",
        "Documented": "https://documentedny.com/feed/",
    },

    "Niche / Ideological / Emerging": {
        "Compact Magazine": "https://compactmag.com/feed",
        "Damage Magazine": "https://damagemag.com/feed",  # verify -- low-traffic, may be dark
        "Noema Magazine": "https://www.noemamag.com/feed/",
        "Works in Progress": "https://worksinprogress.co/feed",  # verify
        "Palladium Magazine": "https://www.palladiummag.com/feed/",
    },

    # Meta / Aggregators (Feedly, Pocket, Substack.com, Medium.com,
    # Flipboard) are readers/platforms, not sources -- intentionally
    # excluded. See the Feedly/Inoreader write-up for using them instead.

    "International (Europe, LatAm, Africa, Asia)": {
        "Der Spiegel": "https://www.spiegel.de/international/index.rss",
        "Die Zeit": "https://newsfeed.zeit.de/index",
        "Frankfurter Allgemeine Zeitung": "https://www.faz.net/rss/aktuell/",
        "El País": "https://elpais.com/rss/elpais/portada.xml",
        "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
        "La Repubblica": "https://www.repubblica.it/rss/homepage/rss2.0.xml",
        "Corriere della Sera": "https://xml2.corriereobjects.it/rss/homepage.xml",
        "Le Monde": "https://www.lemonde.fr/rss/une.xml",
        "Le Figaro": "https://www.lefigaro.fr/rss/figaro_actualites.xml",
        "Libération": "https://www.liberation.fr/rss/",
        "Mediapart": "https://www.mediapart.fr/articles/feed",
        "RTVE Noticias": "https://www.rtve.es/api/noticias.rss",  # verify
        "De Volkskrant": "https://www.volkskrant.nl/voorpagina/rss.xml",
        "NRC Handelsblad": "https://www.nrc.nl/rss/",
        "The Irish Times": "https://www.irishtimes.com/rss/",
        "The Sydney Morning Herald": "https://www.smh.com.au/rss/feed.xml",
        "The Australian": "https://www.theaustralian.com.au/feed/",  # verify -- paywalled
        "The Hindu": "https://www.thehindu.com/feeder/default.rss",
        "The Times of India": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "Scroll.in": "https://scroll.in/rss",
    },

    "Global South / Regional Analysis": {
        "Africa Is a Country": "https://africasacountry.com/feed",
        "Mail & Guardian": "https://mg.co.za/feed/",
        "Daily Maverick": "https://www.dailymaverick.co.za/feed/",
        "The Continent": "https://thecontinent.org/feed/",  # verify
        "Folha de S.Paulo": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
        "O Globo": "https://oglobo.globo.com/rss.xml",  # verify
        "La Nación": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/",  # verify
        "Página/12": "https://www.pagina12.com.ar/rss/portada",
        "Animal Político": "https://www.animalpolitico.com/feed/",
        "Aristegui Noticias": "https://aristeguinoticias.com/feed/",
    },

    "Policy / Think Tank": {
        "American Enterprise Institute (AEI)": "https://www.aei.org/feed/",
        "Heritage Foundation": "https://www.heritage.org/rss.xml",  # verify
        "Cato Institute": "https://www.cato.org/rss/blog",
        "Center for American Progress": "https://www.americanprogress.org/feed/",
        "Hoover Institution": "https://www.hoover.org/rss.xml",  # verify
        "Carnegie Endowment for International Peace": "https://carnegieendowment.org/rss/",
        "Chatham House": "https://www.chathamhouse.org/rss/all",
        "Peterson Institute for International Economics": "https://www.piie.com/rss/blogs",
        "Open Markets Institute": "https://www.openmarketsinstitute.org/feed",
        "Niskanen Center": "https://www.niskanencenter.org/feed/",
    },

    "Substack / Newsletters (Political & Cultural)": {
        "The Pragmatic Engineer": "https://newsletter.pragmaticengineer.com/feed",
        "Noahpinion": "https://www.noahpinion.blog/feed",
        "Marginal Revolution": "https://marginalrevolution.com/feed",
        "Astral Codex Ten": "https://astralcodexten.substack.com/feed",
        "The Zvi": "https://thezvi.substack.com/feed",
        "Freddie deBoer": "https://freddiedeboer.substack.com/feed",
        "Paul Krugman Newsletter": "https://paulkrugman.substack.com/feed",
        "The Edgy Optimist (Blake Masters)": "https://mastersinvest.substack.com/feed",
        "Construction Physics": "https://constructionphysics.substack.com/feed",
        "State Capacity": "https://statecapacity.substack.com/feed",
    },

    "Culture + Theory (Deep Criticism)": {
        "e-flux Journal": "https://www.e-flux.com/journal/rss.xml",  # verify
        "Artforum": "https://www.artforum.com/feed",
        "Frieze": "https://www.frieze.com/rss.xml",  # verify
        "Los Angeles Review of Books": "https://lareviewofbooks.org/feed/",
        "The Point Magazine": "https://thepointmag.com/feed/",
        "Boston Review": "https://www.bostonreview.net/feed/",
        "Telos": "https://www.telospress.com/feed/",
        # Critical Inquiry, Representations, and boundary 2 are hosted on
        # academic-press platforms (UChicago Press / UC Press / Duke UP)
        # with no reliable public article feed -- omitted.
    },

    "Video-First / Podcast-Driven": {
        "Pod Save America (Crooked Media)": "https://crooked.com/feed/",
        "The Daily Wire": "https://www.dailywire.com/feeds/rss.xml",  # verify
        "MeidasTouch": "https://meidastouch.com/feed",  # verify
        "The Young Turks": "https://tyt.com/feed",  # verify
        "Channel 4 News (UK)": "https://www.channel4.com/news/feed",
        # Breaking Points, Secular Talk, Valuetainment, and Triggernometry
        # are video/podcast-only -- add a YouTube channel feed by hand if
        # you want them (https://www.youtube.com/feeds/videos.xml?channel_id=...).
        # Novara Media's YouTube arm is covered by the Novara Media entry above.
    },

    "Online Magazines / Digital-Native": {
        "Inverse": "https://www.inverse.com/rss",
        "Mic": "https://www.mic.com/rss",  # verify -- scaled back news ops
        "Bustle Politics": "https://www.bustle.com/rss",
        "Refinery29 Politics": "https://www.refinery29.com/rss.xml",
        "Polygon": "https://www.polygon.com/rss/index.xml",
        "Kotaku": "https://kotaku.com/rss",
        "Vice (news division)": "https://www.vice.com/en/rss",  # verify -- Vice ceased most operations in 2023-24
        "i-D Magazine": "https://i-d.vice.com/en/rss",  # verify -- same Vice Media Group wind-down
        # The Outline and Input Magazine have both shut down -- omitted.
    },

    "Ideological / Niche / Emerging (II)": {
        "American Mind (Claremont Institute)": "https://americanmind.org/feed/",
        "The Lamp Magazine": "https://thelampmagazine.com/feed",  # verify
        "First Things": "https://www.firstthings.com/rss/blogs",
        "Public Discourse": "https://www.thepublicdiscourse.com/feed/",
        "Areo Magazine": "https://areomagazine.com/feed/",
        "Arc Digital": "https://arcdigital.media/feed",
        "The Bulwark": "https://www.thebulwark.com/feed",
        # Compact, Palladium, and Works in Progress are already listed
        # under "Niche / Ideological / Emerging" above -- not repeated.
    },

    "Investigative / Specialized": {
        "ICIJ": "https://www.icij.org/feed/",
        "OCCRP": "https://www.occrp.org/en/rss",
        "The Markup": "https://themarkup.org/feeds/rss.xml",
        "404 Media": "https://www.404media.co/rss/",
        "Tech Policy Press": "https://techpolicy.press/feed",
    },

    # Meta / Curation / Discovery (Memex, Substack Reader, Readwise Reader,
    # RSS.app, Inoreader) are aggregation tools, not sources -- excluded
    # for the same reason as the other META/AGGREGATORS section.

    "Academic Blogs / Theory Platforms": {
        "Post45": "https://post45.org/feed/",
        "Public Seminar": "https://publicseminar.org/feed/",
        "Avidly": "https://avidly.lareviewofbooks.org/feed/",
        "LARB Blog": "https://blog.lareviewofbooks.org/feed/",  # verify -- may mirror main LARB feed
        "Critical Legal Thinking": "https://criticallegalthinking.com/feed/",
        "Crooked Timber": "https://crookedtimber.org/feed/",
        "The Disorder of Things": "https://thedisorderofthings.com/feed/",
        "The Immanent Frame": "https://tif.ssrc.org/feed/",
        # Public Autonomy Project appears inactive with no working feed -- omitted.
        # Africa Is a Country Blog is the same feed as the entry above -- not repeated.
    },

    "Literary + Cultural Theory (Small / Influential)": {
        "The White Review": "https://www.thewhitereview.org/feed/",
        "The Drift": "https://www.thedriftmag.com/feed/",  # verify
        "The New York Review of Books": "https://www.nybooks.com/feed/",
        "The London Review of Books": "https://www.lrb.co.uk/feeds/rss",
        "Asymptote Journal": "https://www.asymptotejournal.com/feed/",  # verify -- quarterly, low volume
        "Music & Literature": "https://www.musicandliterature.org/feed",  # verify
        "Apogee Journal": "https://apogeejournal.org/feed",  # verify
        "Protean Magazine": "https://proteanmag.com/feed/",
        "Bookforum": "https://www.bookforum.com/feed",  # verify -- ceased 2022, relaunched under The Nation in 2023, active again
        # The Offing shut down in 2021 -- omitted.
    },

    "Independent / Small Magazines & Collectives": {
        "Ill Will": "https://illwill.com/feed",  # verify
        "Viewpoint Magazine": "https://viewpointmag.com/feed/",
        "Mute Magazine": "https://www.metamute.org/rss.xml",  # verify
        "Salvage": "https://salvage.zone/feed/",  # verify
        "Plan C": "https://www.weareplanc.org/feed",  # verify
        "Notes from Below": "https://notesfrombelow.org/feed",  # verify
        "Logic(s) Magazine": "https://logicmag.io/feed",  # verify
        "Hard Crackers": "https://hardcrackers.com/feed",  # verify
        "American Compass": "https://americancompass.org/feed/",
        # Endnotes publishes irregularly with no maintained feed -- omitted.
    },

    "Substack / Independent Writers": {
        "Ex Urbe": "https://exurbe.substack.com/feed",
        "The Permanent Crisis": "https://thepermanentcrisis.substack.com/feed",
        "Sinocism": "https://sinocism.com/feed",  # verify
        "ChinaTalk": "https://chinatalk.substack.com/feed",
        "Heatmap News": "https://heatmap.news/rss.xml",  # verify
        "The Ink": "https://the.ink/feed",  # verify
        "The Racket": "https://www.racket.news/feed",
        "Culture Study": "https://culturestudy.substack.com/feed",  # verify
        "Embedded": "https://embedded.substack.com/feed",
        "The Latecomer": "https://thelatecomer.substack.com/feed",
    },

    "Hyper-Niche / Emerging / Experimental": {
        "Xenogothic": "https://xenogothic.com/feed/",
        "The Philosophical Salon": "https://thephilosophicalsalon.com/feed/",
        "3:AM Magazine": "https://www.3ammagazine.com/3am/feed/",
        "Berfrois": "https://www.berfrois.com/feed/",
        "OpenDemocracy": "https://www.opendemocracy.net/en/feed/",
        "Eurozine": "https://www.eurozine.com/feed/",
        "Institute of Art and Ideas": "https://iai.tv/rss",  # verify
        "Aeon": "https://aeon.co/feed.rss",
        "Psyche": "https://psyche.co/feed.rss",  # verify
        # Noema Magazine already appears under "Niche / Ideological /
        # Emerging" above -- not repeated.
    },
}

MAX_ITEMS_PER_FEED = 5   # 230+ sources means even a small per-feed cap adds up fast
MAX_TOTAL_ITEMS = 200


def fetch_all():
    items = []
    ok, skipped = 0, 0
    for category, sources in FEEDS.items():
        for name, url in sources.items():
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                print(f"  [skip] {name}: could not parse ({parsed.bozo_exception})")
                skipped += 1
                continue
            for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                dt = datetime(*published[:6], tzinfo=timezone.utc) if published else datetime.now(timezone.utc)
                items.append({
                    "category": category,
                    "source": name,
                    "title": entry.get("title", "(untitled)"),
                    "link": entry.get("link", url),
                    "summary": entry.get("summary", ""),
                    "date": dt,
                })
            print(f"  [ok]   {name}: {len(parsed.entries)} items")
            ok += 1
    print(f"\n{ok} feeds parsed, {skipped} skipped.")
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:MAX_TOTAL_ITEMS]


def write_html(items, path="combined.html"):
    rows = []
    for it in items:
        rows.append(f"""
        <div class="item">
          <span class="cat">{html.escape(it['category'])}</span>
          <span class="src">{html.escape(it['source'])}</span>
          <span class="date">{it['date'].strftime('%b %d, %H:%M UTC')}</span>
          <h3><a href="{html.escape(it['link'])}" target="_blank" rel="noopener">{html.escape(it['title'])}</a></h3>
        </div>""")
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Combined digest</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 16px;color:#222}}
.item{{border-bottom:1px solid #ddd;padding:14px 0}}
.cat{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#a33;font-weight:600;margin-right:8px}}
.src{{font-size:12px;color:#666}}
.date{{float:right;font-size:11px;color:#999}}
h3{{margin:6px 0 0;font-size:16px}}
a{{color:#222;text-decoration:none}}
a:hover{{text-decoration:underline}}
</style></head><body>
<h1>Combined digest \u2014 generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</h1>
{''.join(rows)}
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def write_rss(items, path="combined.xml"):
    entries = []
    for it in items:
        entries.append(f"""
    <item>
      <title>{html.escape(f"[{it['category']}] {it['title']}")}</title>
      <link>{html.escape(it['link'])}</link>
      <description>{html.escape(f"{it['source']}: {it['summary'][:300]}")}</description>
      <pubDate>{format_datetime(it['date'])}</pubDate>
      <guid isPermaLink="true">{html.escape(it['link'])}</guid>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Political &amp; Cultural Publications \u2014 Combined Digest</title>
  <link>https://example.com</link>
  <description>All categories from the source list, merged into one feed</description>
  <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>
  {''.join(entries)}
</channel></rss>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(feed)


if __name__ == "__main__":
    print("Fetching feeds...")
    all_items = fetch_all()
    write_html(all_items, "combined.html")
    write_html(all_items, "index.html")   # GitHub Pages serves this at the bare repo URL
    write_rss(all_items)
    print(f"\nWrote {len(all_items)} items to combined.html, index.html, and combined.xml")

# --- Keeping it fresh ---------------------------------------------------
# This script is a snapshot: run it, get one merged view, done. To check
# itself automatically (e.g. every morning), wire it up to GitHub Actions
# on a schedule -- see .github/workflows/update.yml alongside this file.
