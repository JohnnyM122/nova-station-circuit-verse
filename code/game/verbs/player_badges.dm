GLOBAL_LIST_EMPTY(player_badges_data)

/proc/load_player_badges(force = FALSE)
	if(!force && length(GLOB.player_badges_data))
		return GLOB.player_badges_data

	if(fexists("config/player_badges.json"))
		var/content = file2text("config/player_badges.json")
		if(content)
			var/list/parsed = json_decode(content)
			if(islist(parsed))
				GLOB.player_badges_data = parsed
				return GLOB.player_badges_data
	return list()

/proc/get_player_badges_record(target_ckey)
	target_ckey = ckey(target_ckey)
	if(!target_ckey)
		return null

	var/list/badges_data = load_player_badges()
	var/list/players = badges_data["players"]
	if(islist(players) && islist(players[target_ckey]))
		return players[target_ckey]

	// Default fallback for any player
	return list(
		"progression" = "🪐 Fresh Arrival",
		"departments" = list(),
		"special" = list()
	)

/proc/get_player_progression_badge(target_ckey)
	target_ckey = ckey(target_ckey)
	if(!target_ckey)
		return null

	var/list/badges_data = load_player_badges()
	var/list/record = get_player_badges_record(target_ckey)
	if(!record)
		return null

	var/prog_name = record["progression"]
	if(!prog_name)
		return null

	var/list/ranks = badges_data["progression_ranks"]
	if(islist(ranks) && islist(ranks[prog_name]))
		var/list/rank_info = ranks[prog_name]
		var/icon_str = rank_info["icon"] || "🪐"
		var/color_str = rank_info["color"] || "#b0c4de"
		return "<span title='[prog_name]' style='color:[color_str]; font-weight:bold; margin-right:3px;'>[icon_str]</span>"

	return null

/datum/player_badges_viewer
	var/client/viewer_client

/datum/player_badges_viewer/New(client/C)
	viewer_client = C

/datum/player_badges_viewer/Topic(href, href_list)
	if(usr?.client != viewer_client)
		return
	if(href_list["inspect_ckey"])
		viewer_client.check_player_badges(href_list["inspect_ckey"])
	else if(href_list["view_reference"])
		viewer_client.view_badge_reference()
	else if(href_list["lookup_honor"])
		viewer_client.lookup_community_honor(href_list["lookup_honor"])

/client/verb/check_player_badges(target_arg as text|null)
	set name = "Check-Player-Badges"
	set category = "OOC"
	set desc = "View badges, progression rank, and community honors for a player."

	var/target_ckey = ""
	if(target_arg)
		target_ckey = ckey(target_arg)

	if(!target_ckey)
		var/list/options = list()
		for(var/client/C in GLOB.clients)
			options["[C.key] (Online)"] = C.ckey
		options["(Custom ckey / Search player...)"] = "__CUSTOM__"

		var/choice = input(src, "Select a player to inspect badges:", "Check Player Badges") as null|anything in options
		if(!choice)
			return
		if(choice == "(Custom ckey / Search player...)")
			var/typed = input(src, "Enter BYOND key or ckey to inspect:", "Inspect Badges") as text|null
			if(!typed)
				return
			target_ckey = ckey(typed)
		else
			target_ckey = options[choice]

	if(!target_ckey)
		return

	var/list/badges_data = load_player_badges()
	var/list/record = get_player_badges_record(target_ckey)
	var/is_online = (GLOB.directory[target_ckey] != null)

	var/client/target_client = GLOB.directory[target_ckey]
	var/display_key = target_client ? target_client.key : target_ckey

	var/prog_name = record["progression"] || "🪐 Fresh Arrival"
	var/list/prog_info = null
	if(islist(badges_data["progression_ranks"]))
		prog_info = badges_data["progression_ranks"][prog_name]

	var/prog_icon = prog_info ? (prog_info["icon"] || "🪐") : "🪐"
	var/prog_color = prog_info ? (prog_info["color"] || "#b0c4de") : "#b0c4de"
	var/prog_desc = prog_info ? (prog_info["desc"] || "Station Member") : "Station Member"

	var/list/dept_badges = record["departments"] || list()
	var/list/special_badges = record["special"] || list()

	var/datum/player_badges_viewer/viewer_datum = new(src)
	var/datum/browser/popup = new(mob, "player_badges_[target_ckey]", "Badges: [display_key]", 640, 680, viewer_datum)

	var/list/html = list()
	html += "<style>"
	html += "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #12151f; color: #e2e8f0; margin: 0; padding: 16px; }"
	html += ".container { max-width: 600px; margin: 0 auto; }"
	html += ".header-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 10px; padding: 18px; margin-bottom: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: space-between; }"
	html += ".player-title { font-size: 20px; font-weight: bold; color: #f8fafc; margin: 0; }"
	html += ".status-tag { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; }"
	html += ".status-online { background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }"
	html += ".status-offline { background-color: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.4); }"
	html += ".section-title { font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin: 18px 0 10px 0; border-bottom: 1px solid #334155; padding-bottom: 4px; }"
	html += ".prog-card { background: #1e293b; border-left: 5px solid [prog_color]; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }"
	html += ".prog-title { font-size: 18px; font-weight: bold; color: [prog_color]; margin-bottom: 4px; }"
	html += ".prog-desc { font-size: 13px; color: #cbd5e1; line-height: 1.4; }"
	html += ".badge-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }"
	html += ".badge-pill { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; display: flex; align-items: flex-start; gap: 12px; }"
	html += ".badge-icon { font-size: 22px; line-height: 1; flex-shrink: 0; margin-top: 2px; }"
	html += ".badge-content { flex: 1; }"
	html += ".badge-name { font-size: 14px; font-weight: 600; margin-bottom: 2px; }"
	html += ".badge-info { font-size: 12px; color: #94a3b8; line-height: 1.3; }"
	html += ".nav-bar { margin-top: 20px; padding-top: 14px; border-top: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }"
	html += ".nav-btn { background: #3b82f6; color: white; text-decoration: none; padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-block; }"
	html += ".nav-btn:hover { background: #2563eb; }"
	html += ".nav-btn-secondary { background: #334155; color: #e2e8f0; }"
	html += ".nav-btn-secondary:hover { background: #475569; }"
	html += ".empty-msg { font-size: 13px; color: #64748b; font-style: italic; padding: 6px 0; }"
	html += "</style>"

	html += "<div class='container'>"
	html += "<div class='header-card'>"
	html += "<div>"
	html += "<div class='player-title'>[display_key]</div>"
	html += "<div style='font-size:12px; color:#64748b; margin-top:2px;'>ckey: [target_ckey]</div>"
	html += "</div>"
	html += "<div class='status-tag [is_online ? "status-online" : "status-offline"]'>[is_online ? "● Online Now" : "○ Offline"]</div>"
	html += "</div>"

	html += "<div class='section-title'>Highest Progression Rank</div>"
	html += "<div class='prog-card'>"
	html += "<div class='prog-title'>[prog_icon] [prog_name]</div>"
	html += "<div class='prog-desc'>[prog_desc]</div>"
	html += "</div>"

	html += "<div class='section-title'>Special Cross-Community Honors</div>"
	if(length(special_badges))
		html += "<div class='badge-grid'>"
		for(var/badge in special_badges)
			var/list/binfo = null
			if(islist(badges_data["special_honors"]))
				binfo = badges_data["special_honors"][badge]
			var/bicon = binfo ? (binfo["icon"] || "🎖️") : "🎖️"
			var/bcolor = binfo ? (binfo["color"] || "#ffd700") : "#ffd700"
			var/bdesc = binfo ? (binfo["desc"] || "Special community honor.") : "Special community honor."
			html += "<div class='badge-pill' style='border-left: 4px solid [bcolor];'>"
			html += "<div class='badge-icon'>[bicon]</div>"
			html += "<div class='badge-content'>"
			html += "<div class='badge-name' style='color:[bcolor];'>[badge]</div>"
			html += "<div class='badge-info'>[bdesc]</div>"
			html += "</div></div>"
		html += "</div>"
	else
		html += "<div class='empty-msg'>No special cross-community honors recorded for this player yet.</div>"

	html += "<div class='section-title'>Department Interest Archetypes</div>"
	if(length(dept_badges))
		html += "<div class='badge-grid'>"
		for(var/badge in dept_badges)
			var/list/dinfo = null
			if(islist(badges_data["department_badges"]))
				dinfo = badges_data["department_badges"][badge]
			var/dicon = dinfo ? (dinfo["icon"] || "🔹") : "🔹"
			var/dcolor = dinfo ? (dinfo["color"] || "#38bdf8") : "#38bdf8"
			var/ddesc = dinfo ? (dinfo["desc"] || "Department specialty.") : "Department specialty."
			html += "<div class='badge-pill' style='border-left: 4px solid [dcolor];'>"
			html += "<div class='badge-icon'>[dicon]</div>"
			html += "<div class='badge-content'>"
			html += "<div class='badge-name' style='color:[dcolor];'>[badge]</div>"
			html += "<div class='badge-info'>[ddesc]</div>"
			html += "</div></div>"
		html += "</div>"
	else
		html += "<div class='empty-msg'>No department badges selected yet.</div>"

	html += "<div class='nav-bar'>"
	html += "<a class='nav-btn nav-btn-secondary' href='?src=\ref[viewer_datum];view_reference=1'>📖 Badge Guide & Reference</a>"
	html += "<a class='nav-btn' href='byond://?command=Check-Player-Badges'>🔍 Check Another Player</a>"
	html += "</div>"

	html += "</div>"

	popup.set_content(html.Join(""))
	popup.open()

/client/verb/view_badge_reference()
	set name = "View-Badge-Reference"
	set category = "OOC"
	set desc = "Browse the complete guide to Nova Station 13 progression, department badges, and Circuit Verse honors."

	var/list/badges_data = load_player_badges()
	var/datum/player_badges_viewer/viewer_datum = new(src)
	var/datum/browser/popup = new(mob, "badge_reference", "Circuit Verse & Nova Station 13 - Badge Reference", 720, 750, viewer_datum)

	var/list/html = list()
	html += "<style>"
	html += "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f1f5f9; margin: 0; padding: 20px; line-height: 1.5; }"
	html += ".container { max-width: 680px; margin: 0 auto; }"
	html += ".hero-header { text-align: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #334155; }"
	html += ".hero-title { font-size: 24px; font-weight: 800; color: #38bdf8; margin: 0 0 6px 0; }"
	html += ".hero-sub { font-size: 13px; color: #94a3b8; }"
	html += ".cat-header { font-size: 16px; font-weight: bold; color: #f8fafc; margin: 24px 0 12px 0; padding: 8px 12px; background: #1e293b; border-left: 4px solid #38bdf8; border-radius: 4px; display: flex; align-items: center; justify-content: space-between; }"
	html += ".card-list { display: flex; flex-direction: column; gap: 8px; }"
	html += ".card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; display: flex; align-items: flex-start; gap: 14px; }"
	html += ".card-icon { font-size: 24px; line-height: 1; flex-shrink: 0; margin-top: 2px; }"
	html += ".card-body { flex: 1; }"
	html += ".card-name { font-size: 15px; font-weight: bold; margin-bottom: 2px; }"
	html += ".card-desc { font-size: 12.5px; color: #cbd5e1; }"
	html += ".lookup-link { font-size: 11px; color: #38bdf8; text-decoration: none; margin-left: 8px; font-weight: normal; }"
	html += ".lookup-link:hover { text-decoration: underline; }"
	html += ".footer-note { margin-top: 24px; padding: 14px; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; font-size: 12px; color: #93c5fd; }"
	html += "</style>"

	html += "<div class='container'>"
	html += "<div class='hero-header'>"
	html += "<div class='hero-title'>🌌 Circuit Verse Badge Reference</div>"
	html += "<div class='hero-sub'>Official guide to Nova Station 13 crew progression, player archetypes, and community honors.</div>"
	html += "</div>"

	// Progression Ranks
	html += "<div class='cat-header'><span>🚀 Nova Station 13 Crew Progression</span><span style='font-size:11px; color:#94a3b8; font-weight:normal;'>Earned via activity & dedication</span></div>"
	html += "<div class='card-list'>"
	var/list/prog_ranks = badges_data["progression_ranks"]
	if(islist(prog_ranks))
		for(var/rank_name in prog_ranks)
			var/list/rinfo = prog_ranks[rank_name]
			var/ricon = rinfo["icon"] || "🪐"
			var/rcolor = rinfo["color"] || "#b0c4de"
			var/rdesc = rinfo["desc"] || ""
			html += "<div class='card' style='border-left: 4px solid [rcolor];'>"
			html += "<div class='card-icon'>[ricon]</div>"
			html += "<div class='card-body'>"
			html += "<div class='card-name' style='color:[rcolor];'>[rank_name] <a class='lookup-link' href='?src=\ref[viewer_datum];lookup_honor=[url_encode(rank_name)]'>(View Holders)</a></div>"
			html += "<div class='card-desc'>[rdesc]</div>"
			html += "</div></div>"
	html += "</div>"

	// Department Archetypes
	html += "<div class='cat-header'><span>🛠️ Department Interest Archetypes</span><span style='font-size:11px; color:#94a3b8; font-weight:normal;'>Self-assigned player interests</span></div>"
	html += "<div class='card-list'>"
	var/list/dept_badges = badges_data["department_badges"]
	if(islist(dept_badges))
		for(var/dname in dept_badges)
			var/list/dinfo = dept_badges[dname]
			var/dicon = dinfo["icon"] || "🔹"
			var/dcolor = dinfo["color"] || "#38bdf8"
			var/ddesc = dinfo["desc"] || ""
			html += "<div class='card' style='border-left: 4px solid [dcolor];'>"
			html += "<div class='card-icon'>[dicon]</div>"
			html += "<div class='card-body'>"
			html += "<div class='card-name' style='color:[dcolor];'>[dname] <a class='lookup-link' href='?src=\ref[viewer_datum];lookup_honor=[url_encode(dname)]'>(View Holders)</a></div>"
			html += "<div class='card-desc'>[ddesc]</div>"
			html += "</div></div>"
	html += "</div>"

	// Special Honors
	html += "<div class='cat-header'><span>🎖️ Special Cross-Community Honors</span><span style='font-size:11px; color:#94a3b8; font-weight:normal;'>Awarded across all Circuit Verse servers</span></div>"
	html += "<div class='card-list'>"
	var/list/special_honors = badges_data["special_honors"]
	if(islist(special_honors))
		for(var/sname in special_honors)
			var/list/sinfo = special_honors[sname]
			var/sicon = sinfo["icon"] || "🎖️"
			var/scolor = sinfo["color"] || "#ffd700"
			var/sdesc = sinfo["desc"] || ""
			html += "<div class='card' style='border-left: 4px solid [scolor];'>"
			html += "<div class='card-icon'>[sicon]</div>"
			html += "<div class='card-body'>"
			html += "<div class='card-name' style='color:[scolor];'>[sname] <a class='lookup-link' href='?src=\ref[viewer_datum];lookup_honor=[url_encode(sname)]'>(View Holders)</a></div>"
			html += "<div class='card-desc'>[sdesc]</div>"
			html += "</div></div>"
	html += "</div>"

	html += "<div class='footer-note'>"
	html += "<b>About Badges & Progression:</b> Badges represent participation, community dedication, and roleplay passion. They do not grant in-game mechanical authority or staff powers. Progression displays automatically beside your name in OOC!"
	html += "</div>"

	html += "</div>"

	popup.set_content(html.Join(""))
	popup.open()

/client/verb/lookup_community_honor(honor_name as text|null)
	set name = "Lookup-Community-Honor"
	set category = "OOC"
	set desc = "Look up a specific community honor or badge to see its meaning and all holders."

	var/list/badges_data = load_player_badges()
	var/list/all_badges = list()

	if(islist(badges_data["special_honors"]))
		for(var/b in badges_data["special_honors"])
			all_badges[b] = "special"
	if(islist(badges_data["progression_ranks"]))
		for(var/b in badges_data["progression_ranks"])
			all_badges[b] = "progression"
	if(islist(badges_data["department_badges"]))
		for(var/b in badges_data["department_badges"])
			all_badges[b] = "department"

	if(!honor_name)
		var/choice = input(src, "Select a badge or honor to look up:", "Lookup Community Honor") as null|anything in all_badges
		if(!choice)
			return
		honor_name = choice

	var/badge_type = all_badges[honor_name]
	var/list/badge_info = null
	if(badge_type == "special")
		badge_info = badges_data["special_honors"][honor_name]
	else if(badge_type == "progression")
		badge_info = badges_data["progression_ranks"][honor_name]
	else if(badge_type == "department")
		badge_info = badges_data["department_badges"][honor_name]

	var/bicon = badge_info ? (badge_info["icon"] || "🔹") : "🔹"
	var/bcolor = badge_info ? (badge_info["color"] || "#38bdf8") : "#38bdf8"
	var/bdesc = badge_info ? (badge_info["desc"] || "") : ""

	// Find holders
	var/list/holders = list()
	var/list/players = badges_data["players"]
	if(islist(players))
		for(var/target_ckey in players)
			var/list/prec = players[target_ckey]
			if(!islist(prec))
				continue
			if(badge_type == "progression" && prec["progression"] == honor_name)
				holders += target_ckey
			else if(badge_type == "special" && islist(prec["special"]) && (honor_name in prec["special"]))
				holders += target_ckey
			else if(badge_type == "department" && islist(prec["departments"]) && (honor_name in prec["departments"]))
				holders += target_ckey

	var/datum/player_badges_viewer/viewer_datum = new(src)
	var/datum/browser/popup = new(mob, "badge_lookup_[ckey(honor_name)]", "Honor Lookup: [honor_name]", 560, 520, viewer_datum)

	var/list/html = list()
	html += "<style>"
	html += "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f1f5f9; margin: 0; padding: 18px; }"
	html += ".card { background: #1e293b; border-left: 5px solid [bcolor]; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }"
	html += ".title { font-size: 20px; font-weight: bold; color: [bcolor]; margin-bottom: 6px; }"
	html += ".desc { font-size: 13px; color: #cbd5e1; line-height: 1.4; }"
	html += ".holders-header { font-size: 14px; font-weight: bold; color: #94a3b8; text-transform: uppercase; margin: 18px 0 10px 0; border-bottom: 1px solid #334155; padding-bottom: 4px; }"
	html += ".holder-item { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }"
	html += ".holder-link { color: #38bdf8; text-decoration: none; font-weight: bold; }"
	html += ".holder-link:hover { text-decoration: underline; }"
	html += "</style>"

	html += "<div class='card'>"
	html += "<div class='title'>[bicon] [honor_name]</div>"
	html += "<div class='desc'>[bdesc]</div>"
	html += "</div>"

	html += "<div class='holders-header'>Recipients / Holders ([length(holders)])</div>"
	if(length(holders))
		for(var/h_ckey in holders)
			var/is_online = (GLOB.directory[h_ckey] != null)
			html += "<div class='holder-item'>"
			html += "<a class='holder-link' href='?src=\ref[viewer_datum];inspect_ckey=[h_ckey]'>[h_ckey]</a>"
			html += "<span style='font-size:11px; color:[is_online ? "#4ade80" : "#64748b"];'>[is_online ? "Online Now" : "Offline"]</span>"
			html += "</div>"
	else
		html += "<div style='color:#64748b; font-size:13px; font-style:italic;'>No players have been registered for this honor yet.</div>"

	html += "<div style='margin-top:16px;'><a style='color:#94a3b8; font-size:12px; text-decoration:none;' href='?src=\ref[viewer_datum];view_reference=1'>← Back to Badge Reference</a></div>"

	popup.set_content(html.Join(""))
	popup.open()

/client/verb/reload_player_badges()
	set name = "Reload-Player-Badges"
	set category = "Admin"
	set desc = "Reloads player badges data from config/player_badges.json."

	if(!check_rights(R_ADMIN|R_SERVER, TRUE))
		return

	load_player_badges(force = TRUE)
	to_chat(src, SPAN_NOTICE("Player badges configuration reloaded successfully."))
	log_admin("[key_name(src)] reloaded player badges from config/player_badges.json.")
	message_admins("[key_name_admin(src)] reloaded player badges from config/player_badges.json.")
