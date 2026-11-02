/datum/world_topic_handler/ban
	topic_key = "ban"
	requires_commskey = TRUE

/datum/world_topic_handler/ban/execute(list/input, key_valid)
	/*
	Handles issuing bans from Discord bot.
	Expected parameters:
		ckey: target ckey
		bantype: "TEMPBAN", "PERMABAN", "JOB_TEMPBAN", "JOB_PERMABAN"
		duration: minutes (integer, 0 for permanent)
		reason: reason string
		sender: admin Discord name or ckey
		job: job name if job ban
	*/
	var/target_ckey = ckey(input["ckey"])
	if(!target_ckey)
		return json_encode(list("error" = "No valid ckey provided"))

	var/bantype = input["bantype"] ? uppertext(input["bantype"]) : "TEMPBAN"
	var/duration = text2num(input["duration"])
	if(isnull(duration))
		duration = 0

	var/reason = sanitize(input["reason"])
	if(!reason)
		reason = "Banned via Discord by Staff"

	var/sender = sanitize(input["sender"])
	if(!sender)
		sender = "Discord Admin"

	var/job = input["job"] ? sanitize(input["job"]) : null

	// Validate bantype
	var/is_jobban = (bantype == "JOB_TEMPBAN" || bantype == "JOB_PERMABAN")
	if(is_jobban && !job)
		return json_encode(list("error" = "Job must be specified for job bans"))

	var/computerid = ""
	var/ip = ""
	var/client/target_client = GLOB.directory[target_ckey]

	if(target_client)
		computerid = target_client.computer_id
		ip = target_client.address
	else
		// Check player table for offline user
		var/datum/db_query/query_check = SSdbcore.NewQuery("SELECT computerid, ip FROM player WHERE ckey = :ckey", list("ckey" = target_ckey))
		if(query_check.warn_execute() && query_check.NextRow())
			computerid = query_check.item[1]
			ip = query_check.item[2]
		qdel(query_check)

	var/serverip = "[world.internet_address]:[world.port]"
	var/server_id = GLOB.configuration.system.instance_id

	var/sql_bantype = bantype
	// Map to DB bantype
	switch(bantype)
		if("TEMPBAN")
			sql_bantype = "TEMPBAN"
		if("PERMABAN")
			sql_bantype = "PERMABAN"
		if("JOB_TEMPBAN")
			sql_bantype = "JOB_TEMPBAN"
		if("JOB_PERMABAN")
			sql_bantype = "JOB_PERMABAN"

	var/expiration_sql = (duration > 0) ? "Now() + INTERVAL :duration MINUTE" : "null"

	var/datum/db_query/query_insert = SSdbcore.NewQuery({"
		INSERT INTO ban (`id`,`bantime`,`serverip`,`bantype`,`reason`,`job`,`duration`,`rounds`,`expiration_time`,`ckey`,`computerid`,`ip`,`a_ckey`,`a_computerid`,`a_ip`,`who`,`adminwho`,`edits`,`unbanned`,`unbanned_datetime`,`unbanned_ckey`,`unbanned_computerid`,`unbanned_ip`,`ban_round_id`,`unbanned_round_id`, `server_id`)
		VALUES (null, Now(), :serverip, :bantype, :reason, :job, :duration, 0, "} + expiration_sql + {", :ckey, :computerid, :ip, :a_ckey, 'DISCORD', '127.0.0.1', '', '', '', null, null, null, null, null, :roundid, null, :server_id)
	"}, list(
		"serverip" = serverip,
		"bantype" = sql_bantype,
		"reason" = reason,
		"job" = job,
		"duration" = "[duration]",
		"ckey" = target_ckey,
		"computerid" = computerid ? computerid : "",
		"ip" = ip ? ip : "",
		"a_ckey" = sender,
		"roundid" = GLOB.round_id,
		"server_id" = server_id
	))

	if(!query_insert.warn_execute())
		qdel(query_insert)
		return json_encode(list("error" = "Failed to insert ban into database"))

	qdel(query_insert)

	// Admin announcement in-game
	var/duration_text = (duration > 0) ? "([duration] minutes)" : "(Permanent)"
	var/job_text = job ? "([job])" : ""
	message_admins("<span class='adminnotice'><b>[sender] (Discord)</b> has added a [sql_bantype] for [target_ckey] [job_text] [duration_text] with reason: \"[reason]\"</span>")
	log_admin("[sender] (Discord) added [sql_bantype] for [target_ckey] [job_text] [duration_text] Reason: [reason]")

	// If player is online, handle kick or job removal
	if(target_client)
		if(!is_jobban)
			to_chat(target_client, SPAN_DANGER("<BIG><B>You have been banned by [sender] (Discord).</B></BIG><br>Reason: [reason]<br>[duration_text]"))
			qdel(target_client)
		else
			to_chat(target_client, SPAN_DANGER("<BIG><B>You have been job-banned from [job] by [sender] (Discord).</B></BIG><br>Reason: [reason]<br>[duration_text]"))

	return json_encode(list(
		"success" = TRUE,
		"ckey" = target_ckey,
		"bantype" = sql_bantype,
		"duration" = duration,
		"reason" = reason
	))
