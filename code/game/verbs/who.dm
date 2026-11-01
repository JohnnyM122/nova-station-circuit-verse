/client/verb/who()
	set name = "Who"
	set category = "OOC"

	var/list/lines = list()
	var/list/ckeys = list()

	for(var/client/C in GLOB.clients)
		if(C.holder && C.holder.big_brother) // BB doesn't show up at all
			continue

		if(C.holder && C.holder.fakekey)
			ckeys += C.holder.fakekey
		else
			ckeys += C.key

	ckeys = sortList(ckeys) // Sort it. We dont do this above because fake keys would be out of order, which would be a giveaway

	var/list/output_players = list()

	// Now go over it again to apply colours.
	for(var/player in ckeys)
		var/client/C = GLOB.directory[ckey(player)]
		if(!C)
			// This should NEVER happen, but better to be safe
			continue
		// Get the colour
		var/colour = client2rankcolour(C)
		var/output = "[player]"
		if(C.holder)
			output = "<b>[output]</b>"
		if(colour)
			output = "<font color='[colour]'>[output]</font>"

		output_players += output

	lines += "<b>Current Players ([length(output_players)]): </b>"
	lines += output_players.Join(", ") // Turn players into a comma separated list

	if(check_rights(R_ADMIN, FALSE))
		lines += "Click <a href='byond://?_src_=holder;who_advanced=1'>here</a> for detailed (old) who."

	to_chat(src, lines.Join("<br>"))

// Advanced version of `who` to show player age, antag status and more. Lags the chat when loading, so its in its own proc
/client/proc/who_advanced()
	if(!check_rights(R_ADMIN))
		return

	var/list/Lines = list()

	for(var/client/C in GLOB.clients)
		if(C.holder && C.holder.big_brother && !check_rights(R_PERMISSIONS, FALSE)) // need PERMISSIONS to see BB
			continue

		var/list/entry = list()
		entry += "\t[C.key]"
		if(C.holder && C.holder.fakekey)
			entry += " <i>(as [C.holder.fakekey])</i>"
		entry += " - Playing as [C.mob.real_name]"
		switch(C.mob.stat)
			if(UNCONSCIOUS)
				entry += " - <font color='darkgray'><b>Unconscious</b></font>"
			if(DEAD)
				if(isobserver(C.mob))
					var/mob/dead/observer/observer = C.mob
					if(observer.ghost_flags & GHOST_START_AS_OBSERVER)
						entry += " - <font color='gray'>Observing</font>"
					else
						entry += " - <font color='black'><b>DEAD</b></font>"
				else if(isnewplayer(C.mob))
					entry += " - <font color='green'>New Player</font>"
				else
					entry += " - <font color='black'><b>DEAD</b></font>"

		var/account_age
		if(isnum(C.player_age))
			account_age = C.player_age
		else
			account_age = 0

		if(account_age <= 1)
			account_age = "<font color='#ff0000'><b>[account_age]</b></font>"
		else if(account_age < 10)
			account_age = "<font color='#ff8c00'><b>[account_age]</b></font>"

		entry += " - [account_age]"

		if(is_special_character(C.mob))
			entry += " - <b><font color='red'>Antagonist</font></b>"
		entry += " ([ADMIN_QUE(C.mob, "?")])"

		Lines += entry.Join("")

	var/list/msg = list()

	for(var/line in sortList(Lines))
		msg += "[line]"

	msg += "<b>Total Players: [length(Lines)]</b>"
	to_chat(src, msg.Join("<br>"))

/client/verb/adminwho()
	set category = VERB_CATEGORY_ADMIN
	set name = "Staff Who"

	var/list/managementmsg = list()
	var/list/adminmsg = list()
	var/list/modmsg = list()
	var/list/devmsg = list()
	var/list/mentormsg = list()
	var/list/observermsg = list()

	var/num_management_online = 0
	var/num_admins_online = 0
	var/num_mods_online = 0
	var/num_devs_online = 0
	var/num_mentors_online = 0
	var/num_observers_online = 0

	for(var/client/C in GLOB.admins)
		if(!C?.holder)
			continue
		if(C.holder.fakekey && !check_rights(R_ADMIN|R_MOD|R_STAFF_OBSERVER|R_MANAGEMENT, FALSE)) // Only staff with admin/observer/management perms can see stealthmins
			continue
		if(C.holder.big_brother && !check_rights(R_PERMISSIONS, FALSE)) // Normal admins can't see Big Brother
			continue

		var/list/line = list()
		var/rank_colour = client2rankcolour(C)
		if(rank_colour)
			line += "<font color='[rank_colour]'><b>[C]</b></font> is a [C.holder.rank]"
		else
			line += "<b>[C]</b> is a [C.holder.rank]"

		if(holder) // Only for those with perms see the extra bit
			if(C.holder.fakekey && check_rights(R_ADMIN|R_MOD|R_STAFF_OBSERVER|R_MANAGEMENT, FALSE))
				line += " <i>(as [C.holder.fakekey])</i>"

			if(isobserver(C.mob))
				line += " - Observing"
			else if(isnewplayer(C.mob))
				line += " - Lobby"
			else
				line += " - Playing"

			if(C.is_afk())
				line += " (AFK)"

		line += "<br>"
		var/entry_text = line.Join("")

		var/all_role_bits = (R_MANAGEMENT | R_ADMIN | R_MOD | R_DEV_TEAM | R_MAINTAINER | R_MENTOR | R_STAFF_OBSERVER)
		var/has_everything_wildcard = ((C.holder.rights & all_role_bits) == all_role_bits)

		if(has_everything_wildcard)
			if(findtext(C.holder.rank, "Maintainer") || findtext(C.holder.rank, "Dev"))
				num_devs_online++
				devmsg += entry_text
			else
				num_management_online++
				managementmsg += entry_text
		else if(check_rights_client(R_MANAGEMENT, FALSE, C))
			num_management_online++
			managementmsg += entry_text
		else if(check_rights_client(R_DEV_TEAM|R_MAINTAINER, FALSE, C))
			num_devs_online++
			devmsg += entry_text
		else if(check_rights_client(R_ADMIN, FALSE, C))
			num_admins_online++
			adminmsg += entry_text
		else if(check_rights_client(R_MOD, FALSE, C))
			num_mods_online++
			modmsg += entry_text
		else if(check_rights_client(R_MENTOR, FALSE, C))
			num_mentors_online++
			mentormsg += entry_text
		else if(check_rights_client(R_STAFF_OBSERVER, FALSE, C))
			num_observers_online++
			observermsg += entry_text
		else
			num_observers_online++
			observermsg += entry_text

	var/list/final_message = list()
	if(num_management_online)
		final_message += "<b>Management Staff ([num_management_online]):</b><br>"
		final_message += managementmsg
		final_message += "<br>"
	if(num_admins_online)
		final_message += "<b>Administration ([num_admins_online]):</b><br>"
		final_message += adminmsg
		final_message += "<br>"
	if(num_mods_online)
		final_message += "<b>Moderation Staff ([num_mods_online]):</b><br>"
		final_message += modmsg
		final_message += "<br>"
	if(num_devs_online)
		final_message += "<b>Development &amp; Maintenance Team ([num_devs_online]):</b><br>"
		final_message += devmsg
		final_message += "<br>"
	if(num_mentors_online)
		final_message += "<b>Mentors ([num_mentors_online]):</b><br>"
		final_message += mentormsg
		final_message += "<br>"
	if(num_observers_online)
		final_message += "<b>Staff Observers ([num_observers_online]):</b><br>"
		final_message += observermsg
		final_message += "<br>"

	var/num_ticket_admins = num_management_online + num_admins_online + num_mods_online
	if(!num_ticket_admins || !num_mentors_online)
		final_message += SPAN_NOTICE("Even with no [!num_ticket_admins ? "admins" : ""][!num_ticket_admins && !num_mentors_online ? " or " : ""][!num_mentors_online ? "mentors" : ""] online, make a ticket anyways. [!num_ticket_admins ? "Adminhelps" : ""][!num_ticket_admins && !num_mentors_online ? " and " : ""][!num_mentors_online ? "Mentorhelps" : ""] will be relayed to Discord, and staff will still be informed.")
	to_chat(src, final_message.Join(""))
