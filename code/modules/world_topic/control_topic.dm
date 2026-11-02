/datum/world_topic_handler/control
	topic_key = "control"
	requires_commskey = TRUE

/datum/world_topic_handler/control/execute(list/input, key_valid)
	/*
	Handles server administrative controls via Discord.
	Expected parameters:
		action: "announce", "reload_admins", "reboot"
		sender: Discord username or tag
		msg: message content (for announce)
	*/
	var/action = input["action"]
	var/sender = sanitize(input["sender"])
	if(!sender)
		sender = "Discord Staff"

	switch(action)
		if("announce")
			var/raw_msg = input["msg"]
			if(!raw_msg)
				return json_encode(list("error" = "No message provided"))
			var/sanitized_msg = sanitize(raw_msg)
			to_chat(world, "<br><h2 style='color: #00e1ff; text-align: center; border: 2px solid #00e1ff; padding: 5px; background-color: #001f3f;'>📢 Staff Announcement from [sender] (Discord):<br><span style='color: #ffffff;'>[sanitized_msg]</span></h2><br>")
			SEND_SOUND(world, sound('sound/misc/notice2.ogg'))
			log_admin("DISCORD ANNOUNCEMENT: [sender]: [sanitized_msg]")
			return json_encode(list("success" = TRUE))

		if("reload_admins")
			load_admins()
			message_admins("<span class='adminnotice'><b>[sender] (Discord)</b> triggered an admin reload from the database.</span>")
			log_admin("DISCORD ADMIN RELOAD: [sender]")
			return json_encode(list("success" = TRUE))

		if("reboot")
			message_admins("<span class='adminnotice'><b>[sender] (Discord)</b> requested an immediate server reboot.</span>")
			log_admin("DISCORD REBOOT REQUEST: [sender]")
			SSticker.reboot_helper("Reboot requested by [sender] via Discord", "remote reboot")
			return json_encode(list("success" = TRUE))

		if("kick")
			var/target_ckey = ckey(input["ckey"])
			var/raw_reason = input["reason"]
			var/reason = sanitize(raw_reason)
			if(!reason)
				reason = "Kicked by server administration"
			var/kicked = FALSE
			for(var/client/C in GLOB.clients)
				if(C.ckey == target_ckey)
					to_chat(C, "<br><h2 style='color: #ff3333; text-align: center; border: 2px solid #ff3333; padding: 6px; background-color: #2b0000;'>🚫 KICKED FROM SERVER</h2><p style='text-align: center; font-size: 14px; color: #ffffff;'><b>Reason:</b> [reason]<br><br>👉 Circuit Verse Discord: <a href='https://discord.gg/circuitverse' style='color:#5865F2;'><b>https://discord.gg/circuitverse</b></a><br>Please visit the Discord and claim your role in <b>#welcome-channel</b> to reconnect.</p><br>")
					var/kick_html = {"<!DOCTYPE html><html><head><meta charset='utf-8'><style>body{background-color:#16181d;color:#e0e0e0;font-family:'Segoe UI',sans-serif;margin:0;padding:20px;}.header{background:linear-gradient(135deg,#8b0000,#4a0000);color:#fff;padding:16px;border-radius:8px;text-align:center;border:1px solid #ff4444;}.title{font-size:18px;font-weight:bold;margin:0;}.box{background-color:#23272f;border-left:4px solid #ff4444;padding:14px;border-radius:4px;margin:14px 0;line-height:1.6;}.button{display:block;width:75%;margin:20px auto 0 auto;background-color:#5865F2;color:#fff;text-align:center;padding:12px;font-size:15px;font-weight:bold;text-decoration:none;border-radius:6px;}.footer{font-size:11px;color:#888;text-align:center;margin-top:16px;}</style></head><body><div class='header'><div class='title'>⚠️ KICKED FROM SERVER</div><div style='font-size:13px;margin-top:4px;'>Role Requirement Notification</div></div><div class='box'><b>Reason:</b> "} + "[reason]" + {"<br><br>To reconnect and continue playing, please visit our Discord and claim the required role in <b>#welcome-channel</b>.<br><br>👉 Discord: <b>https://discord.gg/circuitverse</b></div><a class='button' href='https://discord.gg/circuitverse' target='_blank'>Join / Open Discord (discord.gg/circuitverse)</a><div class='footer'>Nova Station 13 • Circuit Verse Enforcement</div></body></html>"}
					C << browse(kick_html, "window=kicked_notice;size=560x440;can_resize=0;can_close=1")
					spawn(25)
						if(C)
							qdel(C)
					kicked = TRUE
					break
			if(kicked)
				message_admins("<span class='adminnotice'><b>[sender] (Discord)</b> kicked player <b>[target_ckey]</b>: [reason]</span>")
				log_admin("DISCORD KICK: [sender] kicked [target_ckey]: [reason]")
				return json_encode(list("success" = TRUE, "kicked" = target_ckey))
			return json_encode(list("error" = "Player not found or not connected"))

		if("reload_access_flags")
			SSdbcore.LoadPlayerAccessFlags()
			message_admins("<span class='adminnotice'><b>[sender] (Discord)</b> reloaded player access flags from database.</span>")
			log_admin("DISCORD RELOAD ACCESS FLAGS: [sender]")
			return json_encode(list("success" = TRUE))

		else
			return json_encode(list("error" = "Unknown action: [action]"))
