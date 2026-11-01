#define DEFAULT_PLAYER_OOC_COLOUR "#075FE5" // Can't initial() a global so we store the default in a macro instead
#define BUG_REPORT_CD (5 MINUTES)
GLOBAL_VAR_INIT(normal_ooc_colour, DEFAULT_PLAYER_OOC_COLOUR)

GLOBAL_VAR_INIT(member_ooc_colour, "#035417")
GLOBAL_VAR_INIT(mentor_ooc_colour, "#00B0EB")
GLOBAL_VAR_INIT(moderator_ooc_colour, "#184880")
GLOBAL_VAR_INIT(admin_ooc_colour, "#b82e00")

#define STAFF_OOC_ICON "<img class='icon misc' style='vertical-align: middle; height: 16px; width: 16px; margin-right: 3px;' src='data:image/png;base64,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' title='Staff Member'>"
/// Returns a gold shade for a donor's OOC star and roster entry.
/proc/donator_level_color(level)
	switch(level)
		if(1)
			return "#FFE082"
		if(2)
			return "#FFD54F"
		if(3)
			return "#FFC107"
		if(4)
			return "#FFB300"
	return "#FFD700"
/client/verb/donator_who()
	set name = "Donator Who"
	set desc = "List donators, their levels, and whether they are online."
	set category = "OOC"
	var/list/donator_levels = load_donator_levels()
	// Include currently connected legacy database donators as well as the configured list.
	for(var/client/C in GLOB.clients)
		if(C.holder || !C.donator_level)
			continue
		if(!donator_levels[C.ckey] || C.donator_level > donator_levels[C.ckey])
			donator_levels[C.ckey] = C.donator_level
	var/list/donator_ckeys = list()
	for(var/donor_ckey in donator_levels)
		donator_ckeys += donor_ckey
	donator_ckeys = sortList(donator_ckeys)
	if(!length(donator_ckeys))
		to_chat(src, "No donators are currently listed.")
		return
	var/list/entries = list()
	for(var/donor_ckey in donator_ckeys)
		var/level = donator_levels[donor_ckey]
		var/status = GLOB.directory[donor_ckey] ? "<font color='#4CAF50'>Online</font>" : "<font color='#9E9E9E'>Offline</font>"
		entries += "<font color='[donator_level_color(level)]'>&#9733;</font> [donor_ckey] - Level [level] - [status]"
	to_chat(src, "<b>Donators ([length(entries)]):</b><br>[entries.Join("<br>")]")

/client/verb/ooc(msg = "" as text)
	set name = "OOC"
	set category = "OOC"

	if(!mob)
		return
	if(IsGuestKey(key))
		to_chat(src, SPAN_DANGER("Guests may not use OOC.") , MESSAGE_TYPE_WARNING, confidential = TRUE)
		return

	if(!check_rights(R_ADMIN|R_MOD, 0))
		if(!GLOB.ooc_enabled)
			to_chat(src, SPAN_DANGER("OOC is globally muted.") , MESSAGE_TYPE_WARNING, confidential = TRUE)
			return
		if(!GLOB.dooc_enabled && (mob.stat == DEAD))
			to_chat(usr, SPAN_DANGER("OOC for dead mobs has been turned off.") , MESSAGE_TYPE_WARNING, confidential = TRUE)
			return
		if(check_mute(ckey, MUTE_OOC))
			to_chat(src, SPAN_DANGER("You cannot use OOC (muted).") , MESSAGE_TYPE_WARNING, confidential = TRUE)
			return

	if(!msg)
		msg = typing_input(src.mob, "", "ooc \"text\"")

	msg = trim(sanitize(copytext_char(msg, 1, MAX_MESSAGE_LEN)))
	if(!msg)
		return

	if(!(prefs.toggles & PREFTOGGLE_CHAT_OOC))
		to_chat(src, SPAN_DANGER("You have OOC muted.") )
		return

	if(!check_rights(R_ADMIN|R_MOD,0))
		if(!GLOB.ooc_enabled)
			to_chat(src, SPAN_DANGER("OOC is globally muted.") )
			return
		if(handle_spam_prevention(msg, MUTE_OOC, OOC_COOLDOWN))
			return
		if(findtext(msg, "byond://"))
			to_chat(src, "<B>Advertising other servers is not allowed.</B>")
			log_admin("[key_name(src)] has attempted to advertise in OOC: [msg]")
			message_admins("[key_name_admin(src)] has attempted to advertise in OOC: [msg]")
			return

	log_ooc(msg, src)
	mob.create_log(OOC_LOG, msg)

	var/display_colour = get_ooc_color()

	for(var/client/C in GLOB.clients)
		if(C.prefs.toggles & PREFTOGGLE_CHAT_OOC)
			var/display_name = key
			var/staff_tag = ""

			if(holder && holder.rights)
				if(!holder.fakekey || (C.holder && (C.holder.rights & R_ADMIN)))
					staff_tag = STAFF_OOC_ICON

			if(prefs.unlock_content)
				if(prefs.toggles & PREFTOGGLE_MEMBER_PUBLIC)
					var/icon/byond = icon('icons/member_content.dmi', "blag")
					display_name = "[bicon(byond)][display_name]"

			if(donator_level > 0)
				if(prefs.toggles & PREFTOGGLE_DONATOR_PUBLIC)
					display_name = "<font color='[donator_level_color(donator_level)]'>&#9733;</font> [display_name]"

			if(holder)
				if(holder.fakekey)
					if(C.holder && C.holder.rights & R_ADMIN)
						display_name = "[holder.fakekey]/([key])"
					else
						display_name = holder.fakekey

			if(GLOB.configuration.general.enable_ooc_emoji)
				msg = emoji_parse(msg)

			to_chat(C, "<font color='[display_colour]'>[SPAN_OOC("[SPAN_PREFIX("OOC:")] [staff_tag]<EM>[display_name]:</EM> [SPAN_MESSAGE("[msg]")]")]</font>")

/client/proc/get_ooc_color()
	if(!holder || holder.fakekey)
		if(prefs.unlock_content && (prefs.toggles & PREFTOGGLE_MEMBER_PUBLIC))
			return GLOB.member_ooc_colour
		return GLOB.normal_ooc_colour
	if(!check_rights(R_ADMIN, FALSE))
		if(check_rights(R_MOD, FALSE))
			return GLOB.moderator_ooc_colour
		return GLOB.mentor_ooc_colour
	if(!GLOB.configuration.admin.allow_admin_ooc_colour)
		return GLOB.admin_ooc_colour
	return prefs.ooccolor

/proc/toggle_ooc()
	GLOB.ooc_enabled = (!GLOB.ooc_enabled)
	if(GLOB.ooc_enabled)
		to_chat(world, "<B>The OOC channel has been globally enabled!</B>")
	else
		to_chat(world, "<B>The OOC channel has been globally disabled!</B>")

/proc/auto_toggle_ooc(on)
	if(GLOB.configuration.general.auto_disable_ooc && GLOB.ooc_enabled != on)
		toggle_ooc()

/client/verb/looc(msg = "" as text)
	set name = "LOOC"
	set desc = "Local OOC, seen only by those in view."
	set category = "OOC"

	if(!mob)
		return
	if(IsGuestKey(key))
		to_chat(src, SPAN_DANGER("Guests may not use LOOC.") , MESSAGE_TYPE_WARNING, confidential = TRUE)
		return

	if(!check_rights(R_ADMIN|R_MOD,0))
		if(!GLOB.looc_enabled)
			to_chat(src, SPAN_DANGER("LOOC is globally muted.") , MESSAGE_TYPE_WARNING, confidential = TRUE)
			return
		if(!GLOB.dooc_enabled && (mob.stat == DEAD))
			to_chat(usr, SPAN_DANGER("LOOC for dead mobs has been turned off.") , MESSAGE_TYPE_WARNING, confidential = TRUE)
			return
		if(check_mute(ckey, MUTE_OOC))
			to_chat(src, SPAN_DANGER("You cannot use LOOC (muted).") , MESSAGE_TYPE_WARNING, confidential = TRUE)
			return

	if(!msg)
		msg = typing_input(src.mob, "Local OOC, seen only by those in view.", "looc \"text\"")

	msg = trim(sanitize(copytext_char(msg, 1, MAX_MESSAGE_LEN)))
	if(!msg)
		return

	if(!(prefs.toggles & PREFTOGGLE_CHAT_LOOC))
		to_chat(src, SPAN_DANGER("You have LOOC muted.") )
		return

	if(!check_rights(R_ADMIN|R_MOD,0))
		if(handle_spam_prevention(msg, MUTE_OOC, OOC_COOLDOWN))
			return
		if(findtext(msg, "byond://"))
			to_chat(src, "<B>Advertising other servers is not allowed.</B>")
			log_admin("[key_name(src)] has attempted to advertise in LOOC: [msg]")
			message_admins("[key_name_admin(src)] has attempted to advertise in LOOC: [msg]")
			return

	log_looc(msg, src)
	mob.create_log(LOOC_LOG, msg)
	if(isliving(mob))
		for(var/mob/M in viewers(7, mob))
			if(M.client?.prefs.toggles2 & PREFTOGGLE_2_RUNECHAT)
				M.create_chat_message(mob, msg, FALSE, symbol = RUNECHAT_SYMBOL_LOOC)
	var/mob/source = mob.get_looc_source()
	var/list/heard = get_mobs_in_view(7, source)

	var/display_name = key
	if(holder && holder.fakekey)
		display_name = holder.fakekey
	if(mob.stat != DEAD)
		display_name = mob.name

	for(var/client/target in GLOB.clients)
		if(target.prefs.toggles & PREFTOGGLE_CHAT_LOOC)
			var/prefix = ""
			var/admin_stuff = ""
			var/send = 0

			if(target in GLOB.admins)
				if(check_rights(R_ADMIN|R_MOD,0,target.mob))
					admin_stuff += "/([key])"
					if(target != src)
						admin_stuff += " ([admin_jump_link(mob)])"

			if(target.mob in heard)
				send = 1
				if(is_ai(target.mob))
					prefix = " (Core)"

			else if(is_ai(target.mob)) // Special case
				var/mob/living/silicon/ai/A = target.mob
				if(A.eyeobj in hearers(7, source))
					send = 1
					prefix = " (Eye)"

			if(!send && (target in GLOB.admins))
				if(check_rights(R_ADMIN|R_MOD,0,target.mob))
					send = 1
					prefix = "(R)"

			if(send)
				to_chat(target, SPAN_OOC("[SPAN_LOOC("LOOC[SPAN_PREFIX("[prefix]: ")]<em>[display_name][admin_stuff]:</em> [SPAN_MESSAGE("[msg]")]")]"), MESSAGE_TYPE_OOC)


// Ported from /tg/, full credit to SpaceManiac and Timberpoes.
/client/verb/fit_viewport()
	set name = "Fit Viewport"
	set desc = "Fit the size of the map window to match the viewport."
	set category = "Special Verbs"

	// Fetch aspect ratio
	var/list/view_size = getviewsize(view)
	var/aspect_ratio = view_size[1] / view_size[2]

	// Calculate desired pixel width using window size and aspect ratio
	var/list/sizes = params2list(winget(src, "mainwindow.mainvsplit;paramapwindow", "size"))

	// Client closed the window? Some other error? This is unexpected behaviour, let's CRASH with some info.
	if(!sizes["paramapwindow.size"])
		CRASH("sizes does not contain paramapwindow.size key. This means a winget() failed to return what we wanted. --- sizes var: [sizes] --- list contents:[list2params(sizes)] --- sizes length: [length(sizes)]")

	var/list/map_size = splittext(sizes["paramapwindow.size"], "x")

	// Gets the type of zoom we're currently using
	// If it's 0 we do our pixel calculations based off the size of the mapwindow
	// If it's not, we already know how big we want our window to be, since zoom is the exact pixel ratio of the map
	var/icon_size = params2list(winget(src, "mainwindow.mainvsplit;paramapwindow;map", "icon-size")) || 0
	var/zoom_value = text2num(icon_size["map.icon-size"]) / 32

	var/desired_width = 0
	if(zoom_value)
		desired_width = round(view_size[1] * zoom_value * world.icon_size)
	else

		// Looks like we didn't expect paramapwindow.size to be "ixj" where i and j are numbers.
		// If we don't get our expected 2 outputs, let's give some useful error info.
		if(length(map_size) != 2)
			CRASH("map_size of incorrect length --- map_size var: [map_size] --- map_size length: [length(map_size)]")

		var/height = text2num(map_size[2])
		desired_width = round(height * aspect_ratio)

	if(text2num(map_size[1]) == desired_width)
		// Nothing to do.
		return

	var/list/split_size = splittext(sizes["mainwindow.mainvsplit.size"], "x")
	var/split_width = text2num(split_size[1])

	// Avoid auto-resizing the statpanel and chat into nothing.
	desired_width = min(desired_width, split_width - 300)

	// Calculate and apply a best estimate
	// +4 pixels are for the width of the splitter's handle
	var/pct = 100 * (desired_width + 4) / split_width
	winset(src, "mainwindow.mainvsplit", "splitter=[pct]")

	// Apply an ever-lowering offset until we finish or fail
	var/delta
	for(var/safety in 1 to 10)
		var/after_size = winget(src, "paramapwindow", "size")
		map_size = splittext(after_size, "x")
		var/produced_width = text2num(map_size[1])

		if(produced_width == desired_width)
			// Success!
			return
		else if(isnull(delta))
			// Calculate a probably delta based on the difference
			delta = 100 * (desired_width - produced_width) / split_width
		else if((delta > 0 && produced_width > desired_width) || (delta < 0 && produced_width < desired_width))
			// If we overshot, halve the delta and reverse direction
			delta = -delta / 2

	pct += delta
	winset(src, "mainwindow.mainvsplit", "splitter=[pct]")


/mob/proc/get_looc_source()
	return src

/mob/living/silicon/ai/get_looc_source()
	if(eyeobj)
		return eyeobj
	return src

/client/verb/fix_stat_panel()
	set name = "Fix Stat Panel"
	set hidden = TRUE

	init_verbs()

/client/verb/show_own_notes()
	set name = "Show My Notes"
	set desc = "View your public notes."
	set category = "OOC"

	if(!key)
		return
	if(!SSdbcore.IsConnected())
		to_chat(src, SPAN_DANGER("Failed to establish database connection.") )
		return
	var/list/output = list("<!DOCTYPE html>")
	var/datum/db_query/query_get_notes = SSdbcore.NewQuery({"
		SELECT timestamp, notetext, adminckey, last_editor, server, crew_playtime, round_id
		FROM notes WHERE ckey=:targetkey AND deleted=0 AND public=1 ORDER BY timestamp"}, list(
			"targetkey" = ckey
		))
	if(!query_get_notes.warn_execute())
		to_chat(src, SPAN_DANGER("Unfortunately, we were not able to retrieve your notes.") )
		qdel(query_get_notes)
		return
	output += "<h2><center>Notes of [ckey]</center></h2><br><center><font size='1'>Don't discuss warnings or other punishments from the admins in Paradise Discord.</font></center>"
	output += "<hr style='background:#000000; border:0; height:3px'>"
	var/found_notes = FALSE
	while(query_get_notes.NextRow())
		found_notes = TRUE
		var/timestamp = query_get_notes.item[1]
		var/notetext = query_get_notes.item[2]
		var/adminckey = query_get_notes.item[3]
		var/last_editor = query_get_notes.item[4]
		var/server = query_get_notes.item[5]
		var/mins = text2num(query_get_notes.item[6])
		var/round_id = text2num(query_get_notes.item[7])
		output += "<b>[timestamp][round_id ? " (Round [round_id])" : ""] | [server] | [adminckey]"
		if(mins)
			var/playstring = get_exp_format(mins)
			output += " | [playstring] as Crew"
		output += "</b>"

		if(last_editor)
			output += " <font size='1'>Last edit by [last_editor].</font>"
		output += "<br>[replacetext(notetext, "\n", "<br>")]<hr style='background:#000000; border:0; height:1px'>"
	if(!found_notes)
		output += "<b>You have no public notes.</b>"
	qdel(query_get_notes)
	var/datum/browser/popup = new(mob, "show_public_notes", "Public Notes", 900, 500)
	popup.set_content(output.Join(""))
	popup.open()

/client/verb/submitbug()
	set name = "Report a Bug"
	set desc = "Submit a bug report."
	set category = "OOC"
	set hidden = TRUE
	if(!usr?.client)
		return

	if(GLOB.bug_report_time[usr.ckey] && world.time < (GLOB.bug_report_time[usr.client] + BUG_REPORT_CD))
		var/cd_total_time = GLOB.bug_report_time[usr.ckey] + BUG_REPORT_CD - world.time
		var/cd_minutes = round(cd_total_time / (1 MINUTES))
		var/cd_seconds = round((cd_total_time - cd_minutes MINUTES) / (1 SECONDS))
		tgui_alert(usr, "You must wait another [cd_minutes]:[cd_seconds < 10 ? "0" : ""][cd_seconds] minute[cd_minutes < 2 ? "" : "s"] before submitting another bug report", "Bug Report Rate Limit")
		return

	var/datum/tgui_bug_report_form/report = new(usr)

	report.ui_interact(usr)
	return

#undef DEFAULT_PLAYER_OOC_COLOUR
#undef BUG_REPORT_CD
