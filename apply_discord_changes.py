import json
import asyncio
import discord

CONFIG_PATH = "/home/ubuntu/CV-Nova-Helper/config.json"
with open(CONFIG_PATH, "r") as f:
    cfg = json.load(f)

token = cfg.get("bot_token") or cfg.get("token")
guild_id = int(cfg.get("guild_id", 1564605314752585797))

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name} ({client.user.id})")
    guild = client.get_guild(guild_id)
    if not guild:
        print(f"ERROR: Guild {guild_id} not found! Bot might not be in the server.")
        await client.close()
        return

    print(f"Connected to guild: {guild.name} ({guild.id})")

    # Roles
    everyone = guild.default_role
    unt_host = guild.get_role(1568805604447752263)
    unt_manager = guild.get_role(1568805606192848993)
    unt_admin = guild.get_role(1568805607836745910)
    unt_mod = guild.get_role(1568805609158082641)
    unt_staff = guild.get_role(1568805610219372690)
    unt_player = guild.get_role(1568805612312334558)

    founder_role = guild.get_role(1564610713216098394)
    comm_dir_role = guild.get_role(1567482219495301191)

    # 1. Dedicated Ticket Categories
    ticket_cats_info = [
        ("🎫・Community Tickets", [1567491705266245713, 1567491704544698428, 1567474473404338216, 1567475021906186270]),
        ("🎫・MC Staff Tickets", [1567474481180446761, 1567491706935447562, 1567491706335789056, 1567475022405173320, 1567449697101287467]),
        ("🎫・NS13 Staff Tickets", [1567491708814364692, 1567491707803799572, 1567449653233057912, 1567475022724079637, 1567449658639384678]),
        ("🎫・PZ Staff Tickets", [1567692601291702432, 1567692607054942318, 1567692604340969713, 1567692582849351711]),
        ("🎫・Unturned Staff Tickets", [1568805610219372690, 1568805609158082641, 1568805607836745910, 1568805606192848993, 1568805604447752263]),
    ]

    print("\n=== STEP 1: Creating Ticket Categories ===")
    created_ticket_cats = {}
    for cat_name, allowed_role_ids in ticket_cats_info:
        cat = discord.utils.get(guild.categories, name=cat_name)
        if not cat:
            overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_messages=True)
            }
            if founder_role:
                overwrites[founder_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if comm_dir_role:
                overwrites[comm_dir_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            for rid in allowed_role_ids:
                r = guild.get_role(rid)
                if r:
                    overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True)
            cat = await guild.create_category(name=cat_name, overwrites=overwrites)
            print(f"Created Category: {cat.name} ({cat.id})")
        else:
            print(f"Category already exists: {cat.name} ({cat.id})")
        created_ticket_cats[cat_name] = cat
        await asyncio.sleep(2.5)

    print("\n=== STEP 2: Deleting obsolete ticket channels ===")
    channels_to_delete = [
        1566608724108382238, # ns13-staff-tickets
        1567472426734977114, # mc-staff-tickets
        1567702382266155081, # pz-staff-tickets
        1568805629508849787, # unturned-staff-tickets
    ]
    for ch_id in channels_to_delete:
        ch = guild.get_channel(ch_id)
        if ch:
            try:
                await ch.delete(reason="Replaced by dedicated department ticket category")
                print(f"Deleted obsolete ticket channel: {ch.name} ({ch_id})")
            except Exception as e:
                print(f"Could not delete channel {ch_id}: {e}")
        else:
            print(f"Channel {ch_id} not found or already deleted.")
        await asyncio.sleep(2.5)

    print("\n=== STEP 3: Configuring Unturned Staff Area ===")
    unt_staff_cat = guild.get_channel(1568805616443596880)
    if unt_staff_cat and isinstance(unt_staff_cat, discord.CategoryChannel):
        # Restrict Category to Unturned Server Staff
        await unt_staff_cat.set_permissions(everyone, view_channel=False)
        if unt_staff:
            await unt_staff_cat.set_permissions(unt_staff, view_channel=True, send_messages=True, read_message_history=True)
        print("Restricted Unturned Staff Area category to Unturned Server Staff")

        # Create/Configure channels:
        # 1. 📋・unturned-staff-info
        info_ch = discord.utils.get(unt_staff_cat.channels, name="📋・unturned-staff-info") or discord.utils.get(unt_staff_cat.channels, name="unturned-staff-info")
        if not info_ch:
            info_overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }
            if unt_staff:
                info_overwrites[unt_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
            if unt_admin:
                info_overwrites[unt_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
            if unt_manager:
                info_overwrites[unt_manager] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
            if unt_host:
                info_overwrites[unt_host] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
            info_ch = await guild.create_text_channel(name="📋・unturned-staff-info", category=unt_staff_cat, overwrites=info_overwrites)
            print(f"Created {info_ch.name} ({info_ch.id})")
            await asyncio.sleep(2.5)
        else:
            print(f"Channel {info_ch.name} already exists.")

        # 2. 💼・unturned-management
        mgmt_ch = discord.utils.get(unt_staff_cat.channels, name="💼・unturned-management") or discord.utils.get(unt_staff_cat.channels, name="unturned-management")
        if not mgmt_ch:
            mgmt_overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }
            if unt_staff:
                mgmt_overwrites[unt_staff] = discord.PermissionOverwrite(view_channel=False)
            if unt_mod:
                mgmt_overwrites[unt_mod] = discord.PermissionOverwrite(view_channel=False)
            if unt_admin:
                mgmt_overwrites[unt_admin] = discord.PermissionOverwrite(view_channel=False)
            if unt_manager:
                mgmt_overwrites[unt_manager] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if unt_host:
                mgmt_overwrites[unt_host] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if founder_role:
                mgmt_overwrites[founder_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if comm_dir_role:
                mgmt_overwrites[comm_dir_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            mgmt_ch = await guild.create_text_channel(name="💼・unturned-management", category=unt_staff_cat, overwrites=mgmt_overwrites)
            print(f"Created {mgmt_ch.name} ({mgmt_ch.id})")
            await asyncio.sleep(2.5)
        else:
            print(f"Channel {mgmt_ch.name} already exists.")

        # 3. 🛡️・unturned-administration
        admin_ch = discord.utils.get(unt_staff_cat.channels, name="🛡️・unturned-administration") or discord.utils.get(unt_staff_cat.channels, name="unturned-administration")
        if not admin_ch:
            admin_overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }
            if unt_staff:
                admin_overwrites[unt_staff] = discord.PermissionOverwrite(view_channel=False)
            if unt_mod:
                admin_overwrites[unt_mod] = discord.PermissionOverwrite(view_channel=False)
            if unt_admin:
                admin_overwrites[unt_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if unt_manager:
                admin_overwrites[unt_manager] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if unt_host:
                admin_overwrites[unt_host] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if founder_role:
                admin_overwrites[founder_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            admin_ch = await guild.create_text_channel(name="🛡️・unturned-administration", category=unt_staff_cat, overwrites=admin_overwrites)
            print(f"Created {admin_ch.name} ({admin_ch.id})")
            await asyncio.sleep(2.5)
        else:
            print(f"Channel {admin_ch.name} already exists.")

        # 4. ⚖️・unturned-moderation
        mod_ch = discord.utils.get(unt_staff_cat.channels, name="⚖️・unturned-moderation") or discord.utils.get(unt_staff_cat.channels, name="unturned-moderation")
        if not mod_ch:
            mod_overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }
            if unt_staff:
                mod_overwrites[unt_staff] = discord.PermissionOverwrite(view_channel=False)
            if unt_mod:
                mod_overwrites[unt_mod] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if unt_admin:
                mod_overwrites[unt_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if unt_manager:
                mod_overwrites[unt_manager] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if unt_host:
                mod_overwrites[unt_host] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            if founder_role:
                mod_overwrites[founder_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            mod_ch = await guild.create_text_channel(name="⚖️・unturned-moderation", category=unt_staff_cat, overwrites=mod_overwrites)
            print(f"Created {mod_ch.name} ({mod_ch.id})")
            await asyncio.sleep(2.5)
        else:
            print(f"Channel {mod_ch.name} already exists.")

        # 5. Restrict 📑・unturned-staff-logs to Server Manager and above
        logs_ch = guild.get_channel(1568805627810029569)
        if logs_ch:
            await logs_ch.set_permissions(everyone, view_channel=False)
            await asyncio.sleep(1)
            if unt_staff:
                await logs_ch.set_permissions(unt_staff, view_channel=False)
                await asyncio.sleep(1)
            if unt_mod:
                await logs_ch.set_permissions(unt_mod, view_channel=False)
                await asyncio.sleep(1)
            if unt_admin:
                await logs_ch.set_permissions(unt_admin, view_channel=False)
                await asyncio.sleep(1)
            if unt_manager:
                await logs_ch.set_permissions(unt_manager, view_channel=True, read_message_history=True)
                await asyncio.sleep(1)
            if unt_host:
                await logs_ch.set_permissions(unt_host, view_channel=True, read_message_history=True)
                await asyncio.sleep(1)
            print(f"Restricted {logs_ch.name} to Server Manager and above")

    print("\n=== STEP 4: Configuring Unturned Player Area ===")
    unt_public_cat = guild.get_channel(1568805615164334171)
    if unt_public_cat and isinstance(unt_public_cat, discord.CategoryChannel):
        # Deny @everyone
        await unt_public_cat.set_permissions(everyone, view_channel=False)
        await asyncio.sleep(1.5)
        # Allow Unturned Player
        if unt_player:
            await unt_public_cat.set_permissions(unt_player, view_channel=True, send_messages=True, read_message_history=True)
            await asyncio.sleep(1.5)
        # Allow Unturned Staff
        if unt_staff:
            await unt_public_cat.set_permissions(unt_staff, view_channel=True, send_messages=True, read_message_history=True)
            await asyncio.sleep(1.5)
        print("Protected Unturned Player Area: Denied @everyone, allowed Unturned Player role & Staff")

    print("\nALL DISCORD UPDATES APPLIED SUCCESSFULLY!")
    await client.close()

client.run(token)
