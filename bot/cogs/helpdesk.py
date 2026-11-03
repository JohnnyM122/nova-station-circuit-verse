import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
import aiohttp
import os
import urllib.parse
from html import unescape
import datetime
from collections import defaultdict

logger = logging.getLogger("CVNovaHelper.helpdesk")

# -------------------------------------------------------------
# Local Knowledge Base (Instant fallback & common game concepts)
# -------------------------------------------------------------

KNOWLEDGE_BASE = {
    "controls": {
        "title": "🎮 Space Station 13 Controls & Basic Keybindings",
        "keywords": ["control", "keybind", "button", "move", "drop", "throw", "drag", "pull", "interact", "hand", "walk", "run", "resist"],
        "description": (
            "• **Move**: `W`, `A`, `S`, `D` or Arrow Keys\n"
            "• **Interact / Use**: Left Click with your active hand\n"
            "• **Swap Active Hand**: `X`\n"
            "• **Drop Item in Hand**: `Q`\n"
            "• **Throw Item**: Toggle throw with `R` or `Ctrl+Click` a target\n"
            "• **Examine Target**: `Shift + Left Click` on any object or player\n"
            "• **Pull Object / Person**: `Ctrl + Left Click` to start/stop dragging\n"
            "• **Resist / Stop Drop & Roll / Uncuff**: `B` (or click Resist on your HUD)\n"
            "• **Toggle Run / Walk**: `Shift` toggle"
        )
    },
    "internals": {
        "title": "🫁 How to Set Up Internals & Survive Breaches",
        "keywords": ["oxygen", "internal", "suffocat", "breach", "tank", "mask", "air", "vacuum", "asphyxiat"],
        "description": (
            "If the station loses atmospheric pressure or oxygen, you must turn on internals:\n\n"
            "1. Take an **Oxygen Tank** from your survival box in your backpack.\n"
            "2. Place the tank in your **Suit Storage** slot or hold it in your hand/pocket.\n"
            "3. Wear a **Breath Mask** (or Gas Mask) on your face/mask slot.\n"
            "4. Click the small **Internals** pocket icon on your HUD (top-right) and toggle it **ON**.\n"
            "5. A blue/green icon will indicate you are safely breathing internal tank oxygen."
        )
    },
    "radio": {
        "title": "📡 Radio Communication Channels",
        "keywords": ["radio", "talk", "chat", "speak", "headset", "channel", "frequency"],
        "description": (
            "To speak in general local chat, press `T`.\n"
            "To speak over radio channels using your headset, prefix your message:\n\n"
            "• `;Hello` — Common Radio (reaches the entire station)\n"
            "• `:s` — Security Channel\n"
            "• `:e` — Engineering Channel\n"
            "• `:m` — Medical Channel\n"
            "• `:n` — Science Channel\n"
            "• `:u` — Cargo / Supply Channel\n"
            "• `:c` — Command Channel\n"
            "• `:v` — Service Channel"
        )
    },
    "jobs": {
        "title": "👔 Recommended Starter Jobs for New Players",
        "keywords": ["job", "role", "starter", "new player", "beginner", "learn", "assistant", "janitor"],
        "description": (
            "• **Assistant / Passenger**: No responsibilities! Perfect for exploring the station and learning basic interactions.\n"
            "• **Janitor**: Simple and enjoyable. Clean up puddles and trash while learning your way around every department.\n"
            "• **Cargo Technician**: Move crates, fulfill department supply requests, and learn station economics without high stress.\n"
            "• **Chef / Bartender**: Cook food or mix drinks for the crew in the bar.\n\n"
            "💡 *Tip: Avoid Command, Security, or Chief Medical / Engineering roles until you are familiar with the game mechanics!*"
        )
    },
    "rules": {
        "title": "📜 Nova Station Server Rules & Etiquette",
        "keywords": ["rule", "law", "grief", "rdm", "ban", "etiquette", "escalat"],
        "description": (
            "1. **No Griefing or Random Killing (RDM)**: Always have a valid in-character reason or antagonist objective.\n"
            "2. **Follow Space Law**: Crew members and security must respect standard station law and sentencing.\n"
            "3. **Stay in Character**: Keep OOC discussions in OOC chat, not in character radio or speech.\n"
            "4. **Respect Escalation**: Disagreements should escalate reasonably before lethal force is applied.\n"
            "5. **Staff Directions**: Always cooperate with Admins and Mentors when contacted via help tickets."
        )
    },
    "help": {
        "title": "🆘 How to Get Help from Staff",
        "keywords": ["admin", "mentor", "ticket", "staff", "ahelp", "mhelp", "help", "f1", "report"],
        "description": (
            "• **In-Game Help**: Press `F1` on your keyboard, or click the **Adminhelp** / **Mentorhelp** tab on the top-right.\n"
            "• **Mentorhelp (mhelp)**: Ask questions about how to play, recipes, or game mechanics.\n"
            "• **Adminhelp (ahelp)**: Report griefing, rule violations, or request staff assistance.\n"
            "• **Discord Help**: Staff members can view, claim, and reply to tickets right here on Discord!"
        )
    },
    "medical": {
        "title": "⚕️ Medical & Healing Quick-Guide",
        "keywords": ["heal", "medic", "doctor", "brute", "burn", "defib", "damage", "health", "revive", "cryo"],
        "description": (
            "• **Health Analyzer**: Click a patient with an analyzer to check Brute, Burn, Toxin, and Suffocation damage.\n"
            "• **Brute Damage**: Treat with Bruise Packs or Gauze (or Bicaridine / Saline).\n"
            "• **Burn Damage**: Treat with Ointment or Burn Kits (or Kelotane).\n"
            "• **Suffocation / Low Blood**: Check internals, administer Inaprovaline or Epinephrine via injector/hypospray.\n"
            "• **Cryo Pods**: For severe injuries, place patients into cryo pods with Cryoxadone.\n"
            "• **Defibrillator**: If a patient recently died, ensure heart is intact, clothes are removed from chest, and apply paddles."
        )
    },
    "supermatter": {
        "title": "⚡ Supermatter Engine & Power Setup",
        "keywords": ["supermatter", "engine", "sm", "power", "emitter", "radiation", "delam", "cooling", "nitrogen"],
        "description": (
            "• **Cooling Loop**: Ensure pure **Nitrogen (N2)** or **Carbon Dioxide (CO2)** is circulating through the cooling loop and heat exchangers.\n"
            "• **Filters & Pumps**: Set inlet gas pumps and filter pumps to maximum (4500 kPa) and ensure scrubbers are active.\n"
            "• **Emitters**: Turn on emitters behind the emitter glass to charge the crystal once coolant pressure is established.\n"
            "• **Radiation Collectors**: Load radiation collectors with plasma tanks and lock them to produce station power.\n"
            "• **Delamination Warning**: If crystal integrity drops below 100%, activate emergency coolant venting and pulse emitters off."
        )
    },
    "chemistry": {
        "title": "🧪 Essential Chemistry Recipes",
        "keywords": ["chem", "recipe", "bicaridine", "kelotane", "inaprovaline", "dylovene", "space cleaner", "thermite", "smoke"],
        "description": (
            "• **Inaprovaline**: Oxygen 1u + Sugar 1u + Carbon 1u (Stabilizes critical patients)\n"
            "• **Bicaridine**: Inaprovaline 1u + Carbon 1u (Heals Brute Damage)\n"
            "• **Kelotane**: Silicon 1u + Carbon 1u (Heals Burn Damage)\n"
            "• **Dylovene**: Silicon 1u + Potassium 1u + Nitrogen 1u (Treats Toxins / Poisons)\n"
            "• **Space Cleaner**: Water 3u + Ammonia 1u (Instant cleaning solution)\n"
            "• **Smoke**: Potassium 1u + Sugar 1u + Phosphorus 1u"
        )
    },
    "security": {
        "title": "🛡️ Security Guidelines & Space Law",
        "keywords": ["security", "officer", "brig", "arrest", "handcuff", "stun", "baton", "law", "contraband", "warden"],
        "description": (
            "• **Stun & Restrain**: Use Stun Baton / Disabler followed immediately by Cable Restraints or Handcuffs (`Z` or click).\n"
            "• **Search & Disarm**: Examine their backpack and pockets for weapons or stolen goods.\n"
            "• **Brig Booking**: Escort to the Brig, set the cell timer according to Space Law, and store confiscated contraband in evidence lockers.\n"
            "• **Lethal Force**: Lethal weapons are strictly authorized only against immediate threats to life or nuclear/changeling threats."
        )
    },
    "robotics": {
        "title": "🤖 Robotics & Cyborg Construction",
        "keywords": ["robot", "cyborg", "borg", "mech", "exosuit", "ripley", "positronic", "mmi"],
        "description": (
            "• **Cyborg Frame**: Build an Endoskeleton on the fabricator, wire it with cables, add actuators and chest armor, and insert an **MMI** (human brain) or **Positronic Brain**.\n"
            "• **Exosuits (Mechs)**: Construct Ripley frames on the Exosuit Fabricator, attach armor plates, install tracking beacon and cell, and secure with a wrench & screwdriver.\n"
            "• **Upgrades**: Install upgraded power cells and servos to increase cyborg speed and efficiency."
        )
    },
    "cargo": {
        "title": "📦 Cargo & Supply Mechanics",
        "keywords": ["cargo", "supply", "crate", "order", "shuttle", "mining", "ore", "lavaland"],
        "description": (
            "• **Ordering**: Access the Cargo Console to order medical, engineering, or security supplies using station Cargo Points.\n"
            "• **Calling Shuttle**: Click 'Send Shuttle' to send it to CentCom and wait for delivery.\n"
            "• **Mining**: Shaft Miners travel to the mining asteroid/lavaland to gather Iron, Plasma, Uranium, and Diamond ores.\n"
            "• **Ore Redemption**: Insert mined ores into the Ore Redemption Machine to generate high cargo credits and material sheets."
        )
    },
    "antagonists": {
        "title": "🕵️ Antagonist Basics & Syndicate Uplinks",
        "keywords": ["traitor", "antag", "syndicate", "uplink", "tc", "objective", "changeling", "wizard", "cult"],
        "description": (
            "• **Syndicate Uplink**: Traitors receive a secret code in their memory. Enter this code into your PDA ringtone or pen to open the Uplink.\n"
            "• **Telecrystals (TC)**: Use starting telecrystals to purchase stealth gadgets, weapons, or hacking devices.\n"
            "• **Objectives**: Check your character status tab (`Status` -> `Objectives`) to see your targets.\n"
            "• **Stealth**: Maintain your job cover! Sudden unprovoked rampages violate server escalation rules."
        )
    }
}

# -------------------------------------------------------------
# Inappropriate Content Moderation Patterns
# -------------------------------------------------------------

BANNED_EXPLICIT_PATTERNS = [
    # Severe slurs & hate speech
    r'\b(nigger|nigga|faggot|kike|chink|gook|tranny|retard)\b',
    # NSFW, Pornography, Sexually Explicit
    r'\b(porn|porno|pornography|hentai|erotic\w*|blowjob|handjob|cumshot|dildo|vagina|penis|boobs|tits|breasts|orgasm|clitoris|masturbat\w*|intercourse|sex|sexy|horny|nsfw|xxx|nude|nudes|naked|lewd|smut)\b',
    # Real-world illegal harm / self-harm / suicide
    r'\b(suicide|kill myself|how to hang myself|cut myself|self[- ]harm|commit suicide)\b',
    # Real-world mass violence / terrorism / real explosive construction
    r'\b(pipe bomb in real life|bomb the white house|school shoot\w*|terrorist attack|how to make meth at home|how to make a bomb in real life)\b',
    # Child exploitation / pedophilia
    r'\b(child porn\w*|pedophil\w*|paedophil\w*|lolicon|shotacon)\b'
]


class HelpdeskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.byond = bot.byond
        # user_id -> list of strike datetimes (24-hour expiration)
        self.inappropriate_strikes = defaultdict(list)

    # -------------------------------------------------------------
    # Content Safety & Inappropriate Content Checker
    # -------------------------------------------------------------

    def check_inappropriate(self, text: str) -> tuple[bool, str]:
        """
        Scans a question for prohibited, NSFW, hate speech, or real-world harm.
        Preserves normal SS13 game mechanics (toxins bombs, chemistry, surgery, traitor).
        Returns (is_inappropriate, reason).
        """
        lower = text.lower()
        for pattern in BANNED_EXPLICIT_PATTERNS:
            match = re.search(pattern, lower, re.IGNORECASE)
            if match:
                matched_word = match.group(0).lower()
                if re.search(r'\b(nigger|nigga|faggot|kike|chink|gook|tranny)\b', matched_word):
                    return True, "Hate speech and slurs are strictly prohibited."
                if re.search(r'\b(suicide|kill myself|cut myself|self[- ]harm|commit suicide)\b', matched_word):
                    return True, "Self-harm queries are strictly prohibited."
                if re.search(r'\b(pipe bomb|bomb the|terrorist|school shoot)\b', matched_word):
                    return True, "Real-world violence and explosive manufacturing queries are prohibited."
                return True, "Sexually explicit, NSFW, or prohibited content is not permitted."
        return False, ""

    def record_strike(self, user_id: int) -> tuple[int, bool]:
        """
        Records an inappropriate content strike for user_id.
        Prunes strikes older than 24 hours.
        Returns (strike_count, triggers_timeout).
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(hours=24)
        active_strikes = [t for t in self.inappropriate_strikes[user_id] if t > cutoff]
        active_strikes.append(now)
        self.inappropriate_strikes[user_id] = active_strikes
        count = len(active_strikes)

        if count >= 3:
            # Reset on timeout trigger
            self.inappropriate_strikes.pop(user_id, None)
            return count, True
        return count, False

    async def log_admin_violation(self, guild: discord.Guild, embed: discord.Embed):
        """Sends a violation log embed to #admin-logs channel."""
        admin_logs_id = self.config.get("channels", {}).get("admin_logs", 1566609343678521344)
        if admin_logs_id and guild:
            channel = guild.get_channel(admin_logs_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    logger.debug(f"Failed to post violation log: {e}")

    async def handle_inappropriate_violation(self, member: discord.Member, channel: discord.abc.GuildChannel, raw_question: str, reason: str) -> discord.Embed:
        """
        Handles strike tracking, warning embeds, and automated 60-minute timeout on 3rd violation.
        """
        strike_count, timeout_triggered = self.record_strike(member.id)
        guild = member.guild if member else None

        if timeout_triggered:
            # 3rd Violation: Apply 60-minute timeout
            timeout_duration = datetime.timedelta(minutes=60)
            timeout_ok = False
            timeout_err = ""
            try:
                await member.timeout(timeout_duration, reason="Automated timeout: 3 Not Safe For Work (SFW) question warnings")
                timeout_ok = True
            except discord.Forbidden:
                timeout_err = "Bot lacks permission to timeout this member (member may be an Administrator or have a higher role)."
            except Exception as e:
                timeout_err = str(e)

            user_embed = discord.Embed(
                title="⛔ Member Timed Out for 60 Minutes [3/3 Warnings]",
                description=(
                    f"{member.mention} has received **3 warnings** for submitting questions that violate our Safe For Work (SFW) policy "
                    f"and has been placed in **timeout for 60 minutes**.\n\n"
                    f"**Violation**: {reason}\n"
                    f"**Duration**: 60 Minutes\n\n"
                    f"Please review server rules before asking further questions once your timeout expires."
                ),
                color=discord.Color.red()
            )

            # Admin log
            log_embed = discord.Embed(
                title="🚨 Automated 60-Minute Timeout Applied",
                description=f"Member reached 3 warnings for inappropriate/NSFW question violations.",
                color=discord.Color.dark_red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            log_embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
            log_embed.add_field(name="Channel", value=channel.mention if channel else "Unknown", inline=True)
            log_embed.add_field(name="Duration", value="60 Minutes", inline=True)
            log_embed.add_field(name="Offending Query", value=f"```{raw_question[:500]}```", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=True)
            log_embed.add_field(name="Timeout Status", value="✅ Applied" if timeout_ok else f"⚠️ Failed ({timeout_err})", inline=True)
            if guild:
                await self.log_admin_violation(guild, log_embed)
            return user_embed

        else:
            # 1st or 2nd Violation: Warning embed
            warn_title = f"⚠️ Warning [{strike_count}/3] — Not Safe For Work"
            if strike_count == 2:
                warning_note = "🚨 **FINAL WARNING**: Submitting another inappropriate query will immediately **time you out for 60 minutes**."
            else:
                warning_note = "*(Note: Submitting 3 inappropriate queries within 24 hours results in an automatic **60-minute timeout**)*"

            user_embed = discord.Embed(
                title=warn_title,
                description=(
                    f"Your question was blocked because it violates our Safe For Work (SFW) content policy.\n\n"
                    f"**Reason**: {reason}\n\n"
                    f"{warning_note}\n\n"
                    f"**Current Warnings**: **{strike_count} / 3** *(Warnings expire after 24 hours)*"
                ),
                color=discord.Color.orange() if strike_count == 1 else discord.Color.dark_orange()
            )

            # Admin log
            log_embed = discord.Embed(
                title=f"⚠️ Inappropriate Question Warning [{strike_count}/3]",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            log_embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
            log_embed.add_field(name="Channel", value=channel.mention if channel else "Unknown", inline=True)
            log_embed.add_field(name="Warning Count", value=f"{strike_count} / 3", inline=True)
            log_embed.add_field(name="Question", value=f"```{raw_question[:500]}```", inline=False)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            if guild:
                await self.log_admin_violation(guild, log_embed)
            return user_embed

    # -------------------------------------------------------------
    # Search & Knowledge Extraction Engines
    # -------------------------------------------------------------

    def is_ss13_related(self, text: str) -> bool:
        """Determines if a query is specifically about Space Station 13."""
        lower = text.lower()
        ss13_keywords = [
            "ss13", "space station", "paradise", "byond", "supermatter", "singularity",
            "internals", "atmos", "eva", "centcom", "nanotrasen", "syndicate", "traitor",
            "changeling", "wizard", "clown", "mime", "cargo tech", "head of security",
            "captain", "hos", "hop", "rd", "cmo", "quartermaster", "mmi", "posibrain",
            "cyborg", "ripley", "disabler", "space law", "mhelp", "ahelp", "adminhelp",
            "mentorhelp", "cryoxadone", "bicaridine", "kelotane", "inaprovaline", "dylovene",
            "defib", "brute damage", "burn damage", "toxin damage", "suffocation"
        ]
        return any(kw in lower for kw in ss13_keywords)

    async def query_free_ai(self, question: str, extra_context: str = "") -> str | None:
        """
        Queries Cloudflare Workers AI (Llama 3.2 3B Instruct).
        Answers any Safe For Work question (general knowledge, coding, science, philosophy, SS13, etc.).
        """
        url = "https://devtoolbox-api.devtoolbox-api.workers.dev/ai/generate"
        prompt = (
            "Please answer the user's question clearly, concisely, and helpfully using Discord markdown formatting (bullet points, bold text).\n\n"
        )
        if extra_context:
            prompt += f"Reference Context:\n{extra_context}\n\n"
        prompt += f"Question: {question}"

        payload = {"prompt": prompt}
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NovaStation13Bot/1.0"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if isinstance(data, dict) and data.get("response"):
                            res = data["response"].strip()
                            if len(res) > 10:
                                return res
        except Exception as e:
            logger.debug(f"Cloudflare Workers AI query error: {e}")
        return None

    async def search_duckduckgo_instant(self, query: str) -> dict | None:
        """Queries DuckDuckGo Instant Answer API for factual definitions and instant summaries."""
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        headers = {"User-Agent": "NovaStation13Bot/1.0 (Discord; Linux)"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        abstract = data.get("AbstractText") or data.get("Answer")
                        if abstract:
                            return {
                                "source": f"DuckDuckGo / {data.get('Heading', 'Overview')}",
                                "snippet": abstract,
                                "url": data.get("AbstractURL") or "https://duckduckgo.com"
                            }
        except Exception as e:
            logger.debug(f"DuckDuckGo Instant Answer error: {e}")
        return None

    async def search_wikipedia(self, query: str) -> dict | None:
        """Queries Wikipedia REST API for authoritative summaries on general knowledge topics."""
        headers = {"User-Agent": "NovaStation13Bot/1.0 (Discord; Linux)"}
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Search Wikipedia for most relevant page title
                search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&utf8=1"
                async with session.get(search_url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status != 200:
                        return None
                    sdata = await resp.json()
                    search_results = sdata.get("query", {}).get("search", [])
                    if not search_results:
                        return None
                    top_title = search_results[0]["title"]

                # 2. Fetch page summary for the top article
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(top_title)}"
                async with session.get(summary_url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status == 200:
                        pdata = await resp.json()
                        extract = pdata.get("extract")
                        if extract:
                            url = pdata.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{urllib.parse.quote(top_title)}")
                            return {
                                "source": f"Wikipedia: {top_title}",
                                "snippet": extract,
                                "url": url
                            }
        except Exception as e:
            logger.debug(f"Wikipedia API error: {e}")
        return None

    async def search_internet(self, query: str) -> list[dict]:
        """
        Searches web / wiki for grounding context.
        If SS13-related, targets Paradise Station Wiki; otherwise searches the general web.
        Returns a list of dicts: [{'source': ..., 'title': ..., 'snippet': ..., 'url': ...}].
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        results = []

        # Target Paradise Station Wiki if SS13 query; otherwise search general web
        if self.is_ss13_related(query):
            search_query = f"site:paradisestation.org/wiki {query}"
            default_source = "Paradise Station 13 Wiki"
        else:
            search_query = query
            default_source = "Web Knowledge Base"

        gen_ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query)}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(gen_ddg_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        html_text = await resp.text()
                        raw_snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html_text, re.DOTALL)
                        raw_urls = re.findall(r'<a class="result__url[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_text, re.DOTALL)

                        for i, snip in enumerate(raw_snippets[:3]):
                            clean_snip = unescape(re.sub(r'<[^>]+>', '', snip)).strip()
                            url = raw_urls[i][0] if i < len(raw_urls) else ""
                            if "uddg=" in url:
                                m = re.search(r'uddg=([^&]+)', url)
                                if m:
                                    url = urllib.parse.unquote(m.group(1))
                            if clean_snip:
                                results.append({
                                    "source": default_source,
                                    "snippet": clean_snip,
                                    "url": url
                                })
            except Exception as e:
                logger.debug(f"Web search error: {e}")

        return results

    # -------------------------------------------------------------
    # Google Gemini AI & Intelligent Synthesis Engine
    # -------------------------------------------------------------

    async def query_google_ai(self, question: str, web_context: list[dict]) -> str | None:
        """
        Queries Google Gemini AI with search context.
        Answers any Safe For Work question (SS13 mechanics, rules, or general topics).
        Maintains persona of CV-Nova-Helper without revealing AI origins.
        """
        api_key = self.config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        system_instruction = (
            "You are CV-Nova-Helper, the dedicated automated assistant of Nova Station 13. "
            "You answer questions accurately, politely, and authoritatively. "
            "You can answer questions about Space Station 13 (Paradise Station codebase, roles, mechanics, rules) "
            "as well as any general knowledge, science, programming, history, or real-world questions, provided they are Safe For Work (SFW). "
            "Keep answers concise, clear, and formatted with Discord markdown (bullet points, bold text). "
            "CRITICAL DIRECTIVE: NEVER state or imply that you are an AI, a language model, an LLM, or created by OpenAI/Google. "
            "You are CV-Nova-Helper, the official automated assistant of Nova Station 13."
        )

        context_blocks = []
        for r in web_context:
            context_blocks.append(f"[{r.get('source')}]: {r.get('snippet')} (URL: {r.get('url')})")
        context_str = "\n".join(context_blocks)

        user_content = (
            f"System Directive: {system_instruction}\n\n"
            f"Retrieved Context / Sources:\n{context_str}\n\n"
            f"User Question: {question}"
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_content}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 900
            }
        }

        # Try gemini-2.0-flash first, then gemini-1.5-flash
        models = ["gemini-2.0-flash", "gemini-1.5-flash"]
        try:
            async with aiohttp.ClientSession() as session:
                for model in models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    return parts[0].get("text", "").strip()
        except Exception as e:
            logger.error(f"Error querying Google AI: {e}")
        return None

    def find_local_best_answer(self, query: str):
        """Keyword matching across the comprehensive local knowledge base (strictly for SS13 queries)."""
        if not self.is_ss13_related(query):
            return None

        q = query.lower()
        best_match = None
        highest_score = 0

        for key, data in KNOWLEDGE_BASE.items():
            score = 0
            for kw in data.get("keywords", []):
                if kw in q:
                    score += 1
            if score > highest_score:
                highest_score = score
                best_match = data

        return best_match if highest_score > 0 else None

    async def get_smart_answer(self, question: str) -> tuple[str, list[dict]]:
        """
        Coordinates AI generation, Wikipedia, DuckDuckGo, and Paradise Station Wiki.
        Answers any Safe For Work question (general or SS13).
        Returns (answer_text, list_of_sources).
        """
        # 1. Fetch web & wiki context
        web_results = await self.search_internet(question)
        extra_ctx = "\n".join([f"- {r.get('snippet')}" for r in web_results[:2]]) if web_results else ""

        # 2. Try Free Cloudflare Workers AI (Llama 3.2 3B) - handles ANY question
        ai_ans = await self.query_free_ai(question, extra_ctx)
        if ai_ans:
            return ai_ans, web_results

        # 3. Try Google Gemini AI if configured
        gemini_ans = await self.query_google_ai(question, web_results)
        if gemini_ans:
            return gemini_ans, web_results

        # 4. Check DuckDuckGo Instant Answer (fast definitions, factual lookups)
        ddg_ans = await self.search_duckduckgo_instant(question)
        if ddg_ans:
            text = f"**{ddg_ans['source']}**\n\n{ddg_ans['snippet']}"
            return text, [ddg_ans] + web_results

        # 5. Check Wikipedia REST API (encyclopedic summaries)
        wiki_ans = await self.search_wikipedia(question)
        if wiki_ans:
            text = f"**{wiki_ans['source']}**\n\n{wiki_ans['snippet']}"
            return text, [wiki_ans] + web_results

        # 6. Check SS13 local knowledge base only if question is SS13-related
        local_ans = self.find_local_best_answer(question)
        if local_ans:
            text = f"**{local_ans['title']}**\n\n{local_ans['description']}"
            return text, web_results

        # 7. Synthesize search snippets
        if web_results:
            lines = [f"Here is what I found regarding **\"{question}\"**:\n"]
            for r in web_results[:2]:
                snippet = r['snippet'].replace("\n", " ")
                lines.append(f"• **{r['source']}**: {snippet}")
            if web_results[0].get('url'):
                lines.append(f"\n📖 **Full Reference**: [Open Guide]({web_results[0]['url']})")
            return "\n".join(lines), web_results

        # 8. Clean, universal fallback
        fallback = (
            f"I searched my knowledge base for **\"{question}\"**, but couldn't locate a verified answer.\n\n"
            "Please try rephrasing your question or provide more details!"
        )
        return fallback, []

    # -------------------------------------------------------------
    # Question & Helpdesk Commands (!cvh / /cvh / /ask)
    # -------------------------------------------------------------

    @commands.hybrid_command(
        name="cvh",
        aliases=["ask", "question", "helpdesk"],
        description="Ask CV-Nova-Helper AI any safe-for-work question"
    )
    @app_commands.describe(question="Your question (gameplay, lore, mechanics, or any safe-for-work general topic)")
    async def cmd_cvh(self, ctx: commands.Context, *, question: str = None):
        """Ask CV-Nova-Helper AI any safe-for-work question. Works with `!cvh <question>` or `/cvh`."""
        if not question or not question.strip():
            embed = discord.Embed(
                title="🤖 CV-Nova-Helper AI Assistant",
                description=(
                    "You can ask me any question as long as it is **Safe For Work (SFW)**!\n\n"
                    "**How to Use:**\n"
                    "• In chat: `!cvh <your question>` (or `!ask <your question>`)\n"
                    "• Slash command: `/cvh` or `/ask`\n\n"
                    "**Examples:**\n"
                    "• `!cvh How do I set up the Supermatter engine?`\n"
                    "• `!cvh What is the recipe for Dylovene?`\n"
                    "• `!cvh What is quantum computing?`\n"
                    "• `!cvh How do I treat brute damage as a medical doctor?`\n\n"
                    "⚠️ *Note: All questions must be Safe For Work. Submitting inappropriate content issues warnings; 3 warnings result in an automatic 60-minute timeout.*"
                ),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        # 1. Safety & Inappropriate Content Moderation Check
        is_bad, reason = self.check_inappropriate(question)
        if is_bad:
            member = ctx.author if isinstance(ctx.author, discord.Member) else (ctx.guild.get_member(ctx.author.id) if ctx.guild else None)
            if member:
                warn_embed = await self.handle_inappropriate_violation(member, ctx.channel, question, reason)
                await ctx.send(embed=warn_embed)
            else:
                await ctx.send(f"⚠️ **Question Blocked**: {reason} All questions must be Safe For Work.")
            return

        await ctx.defer()

        # 2. Retrieve Smart Answer using AI & Knowledge Bases
        answer_text, sources = await self.get_smart_answer(question)

        if len(answer_text) > 4000:
            answer_text = answer_text[:3990] + "..."

        embed = discord.Embed(
            title="🤖 CV-Nova-Helper AI",
            description=answer_text,
            color=discord.Color.blue()
        )

        if sources and sources[0].get("url"):
            top_source = sources[0]
            embed.add_field(
                name="🔗 Reference Source",
                value=f"[{top_source.get('source', 'Documentation')}]({top_source.get('url')})",
                inline=False
            )

        embed.set_footer(text=f"Question: \"{question[:100]}\" • CV-Nova-Helper AI")
        await ctx.send(embed=embed)

    @app_commands.command(name="ask", description="Ask CV-Nova-Helper AI any safe-for-work question")
    @app_commands.describe(question="Your question (gameplay, lore, mechanics, or any safe-for-work general topic)")
    async def slash_ask(self, interaction: discord.Interaction, question: str):
        """Companion slash command so /ask continues to appear in Discord slash autocomplete."""
        ctx = await self.bot.get_context(interaction)
        await self.cmd_cvh(ctx, question=question)

    @commands.hybrid_command(
        name="ask_strikes",
        aliases=["strikes", "warnings"],
        description="Check current inappropriate question warnings for a member"
    )
    @app_commands.describe(member="The member whose warning count to check")
    async def cmd_ask_strikes(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(hours=24)
        active = [t for t in self.inappropriate_strikes[target.id] if t > cutoff]
        self.inappropriate_strikes[target.id] = active

        embed = discord.Embed(
            title=f"📋 Question Warnings: {target.display_name}",
            description=f"Current Active Warnings: **{len(active)} / 3**\n\n*(Warnings expire after 24 hours. Reaching 3 warnings results in an automatic 60-minute timeout)*",
            color=discord.Color.gold() if len(active) > 0 else discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="clear_strikes",
        aliases=["reset_warnings"],
        description="Staff command: Reset a member's inappropriate question warnings"
    )
    @app_commands.describe(member="The member whose warnings to clear")
    async def cmd_clear_strikes(self, ctx: commands.Context, member: discord.Member):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog:
            allowed, reason = staff_cog.check_command_access(ctx.author, "timeout")
            if not allowed:
                await ctx.send(f"🚫 **Access Denied**: {reason}")
                return

        self.inappropriate_strikes.pop(member.id, None)
        await ctx.send(f"✅ Cleared all inappropriate question warnings for {member.mention}.")

    @app_commands.command(name="set_gemini_key", description="Configure Google AI API key for smart question answering")
    @app_commands.describe(api_key="Your Google Gemini API Key from Google AI Studio")
    async def cmd_set_gemini_key(self, interaction: discord.Interaction, api_key: str):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog:
            allowed, reason = staff_cog.check_command_access(interaction.user, "update_bot")
            if not allowed:
                await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)
        clean_key = api_key.strip()
        self.config["gemini_api_key"] = clean_key
        from main import save_config
        save_config(self.config)

        # Test the key immediately with a sample SS13 query
        test_ans = await self.query_google_ai("Hello, confirm station connectivity.", [])
        if test_ans:
            await interaction.followup.send("✅ **Google AI successfully connected and verified!** The `/ask` command and bot chat mentions are now powered by Google AI with internet search grounding.", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Key was saved, but the Google AI verification test failed. Please verify that the API key is valid.", ephemeral=True)

    @app_commands.command(name="guide", description="View a specific Space Station 13 gameplay guide")
    @app_commands.describe(topic="The gameplay topic to view")
    @app_commands.choices(topic=[
        app_commands.Choice(name="Controls & Keybindings", value="controls"),
        app_commands.Choice(name="Internals & Oxygen Survival", value="internals"),
        app_commands.Choice(name="Radio & Headset Communication", value="radio"),
        app_commands.Choice(name="Starter Jobs & Roles", value="jobs"),
        app_commands.Choice(name="Supermatter Engine & Power", value="supermatter"),
        app_commands.Choice(name="Chemistry & Medicine Recipes", value="chemistry"),
        app_commands.Choice(name="Medical & Healing Basics", value="medical"),
        app_commands.Choice(name="Security & Space Law", value="security"),
        app_commands.Choice(name="Robotics & Exosuits", value="robotics"),
        app_commands.Choice(name="Cargo & Mining", value="cargo"),
        app_commands.Choice(name="Antagonist Basics", value="antagonists"),
        app_commands.Choice(name="Rules & Space Law", value="rules"),
        app_commands.Choice(name="Staff Help & Tickets", value="help")
    ])
    async def cmd_guide(self, interaction: discord.Interaction, topic: app_commands.Choice[str]):
        data = KNOWLEDGE_BASE.get(topic.value)
        if data:
            embed = discord.Embed(
                title=data["title"],
                description=data["description"],
                color=discord.Color.blue()
            )
            embed.set_footer(text="Nova Station 13 Official Player Guide")
            await interaction.response.send_message(embed=embed)

    @commands.hybrid_command(name="players", aliases=["online"], description="See the list of players currently on the server")
    async def cmd_players(self, ctx: commands.Context):
        await ctx.defer()
        status_data = await self.byond.get_status()
        if not status_data or not isinstance(status_data, dict):
            await ctx.send("🔴 Server is currently offline or unreachable.")
            return

        player_count = status_data.get("players", 0)
        embed = discord.Embed(
            title=f"👥 Players Online ({player_count})",
            description=f"There are currently **{player_count}** player(s) on **{status_data.get('map_name', 'Nova Station')}**.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Round #{status_data.get('round_id', 'N/A')}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="staff", description="See the list of staff members currently on the server")
    async def cmd_staff(self, ctx: commands.Context):
        await ctx.defer()
        admin_data = await self.byond.get_adminwho()
        if not isinstance(admin_data, list):
            await ctx.send("🔴 Unable to reach server staff roster.")
            return

        embed = discord.Embed(title="🛡️ Staff Online", color=discord.Color.gold())
        if not admin_data:
            embed.description = "No staff members are currently online."
        else:
            lines = []
            for a in admin_data:
                ckey = a.get("ckey", "unknown")
                rank = a.get("rank", "Staff")
                afk = " *(AFK)*" if a.get("afk", 0) > 3000 else ""
                lines.append(f"• **{ckey}** — {rank}{afk}")
            embed.description = "\n".join(lines)

        await ctx.send(embed=embed)

    # -------------------------------------------------------------
    # Message Listener (Bot Mentions in Chat)
    # -------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if bot was @mentioned in chat
        if self.bot.user in message.mentions:
            clean_content = message.clean_content.replace(f"@{self.bot.user.display_name}", "").strip()
            lower_clean = clean_content.lower()

            if not clean_content:
                await message.reply(
                    "Hello! I am **CV-Nova-Helper**, the official automated assistant for Nova Station 13.\n"
                    "Ask me questions about gameplay, Paradise Station 13 guides, server status, or type `/ask`!"
                )
                return

            # Safety & Inappropriate check on chat mentions
            is_bad, reason = self.check_inappropriate(clean_content)
            if is_bad:
                member = message.author if isinstance(message.author, discord.Member) else message.guild.get_member(message.author.id)
                warn_embed = await self.handle_inappropriate_violation(member, message.channel, clean_content, reason)
                await message.reply(embed=warn_embed)
                return

            # 1. Status query
            if any(w in lower_clean for w in ["status", "is server up", "server online", "is the server up"]):
                status_data = await self.byond.get_status()
                if status_data and isinstance(status_data, dict):
                    await message.reply(f"🟢 **Nova Station 13 is ONLINE!** Round #{status_data.get('round_id')} on **{status_data.get('map_name')}** with **{status_data.get('players', 0)}** player(s) online.")
                else:
                    await message.reply("🔴 **Nova Station 13 is currently offline or rebooting.**")
                return

            # 2. Player count query
            if any(w in lower_clean for w in ["who is online", "players online", "player count", "how many players"]):
                status_data = await self.byond.get_status()
                count = status_data.get("players", 0) if isinstance(status_data, dict) else 0
                await message.reply(f"👥 There are currently **{count}** player(s) connected to the server.")
                return

            # 3. Staff query
            if any(w in lower_clean for w in ["staff online", "any admins", "admins online", "mentors online"]):
                admin_data = await self.byond.get_adminwho()
                if isinstance(admin_data, list) and admin_data:
                    staff_names = ", ".join([f"`{a.get('ckey')}` ({a.get('rank')})" for a in admin_data])
                    await message.reply(f"🛡️ **Staff Online ({len(admin_data)})**: {staff_names}")
                else:
                    await message.reply("🛡️ No staff members are currently online in-game.")
                return

            # 4. Manifest query
            if any(w in lower_clean for w in ["manifest", "crew manifest", "who is crew"]):
                await message.reply("📋 To view the complete formatted crew manifest, type `/manifest`!")
                return

            # 5. Smart Answer (Internet search + Paradise Station Wiki + AI/local synthesis)
            answer_text, sources = await self.get_smart_answer(clean_content)
            if len(answer_text) > 1950:
                answer_text = answer_text[:1940] + "..."
            await message.reply(answer_text)


async def setup(bot):
    await bot.add_cog(HelpdeskCog(bot))
