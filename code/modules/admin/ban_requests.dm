GLOBAL_LIST_EMPTY(pending_ban_requests)
GLOBAL_VAR_INIT(ban_request_counter, 0)

/datum/ban_request
	var/id
	var/requester_ckey
	var/requester_rank
	var/target_ckey
	var/ban_type
	var/duration = 0
	var/job = ""
	var/reason = ""
	var/timestamp
	var/status = "PENDING"
	var/handled_by = null

/proc/notify_admins_ban_request(datum/ban_request/BR)
	var/duration_text
	if(BR.duration <= 0)
		duration_text = "Permanent"
	else if(BR.duration >= 1440)
		duration_text = "[round(BR.duration / 1440, 0.1)] days ([BR.duration] minutes)"
	else
		duration_text = "[BR.duration] minutes"

	var/msg = "<div style='border: 2px solid #e74c3c; background: rgba(231,76,60,0.15); padding: 8px; margin: 4px; border-radius: 4px;'>"
	msg += "<font color='#e74c3c' size='3'><b>\[!\] BAN APPROVAL REQUEST #[BR.id] \[!\]</b></font><br>"
	msg += "<b>Requester:</b> [BR.requester_ckey] ([BR.requester_rank])<br>"
	msg += "<b>Target Player:</b> <font color='#238afa'><b>[BR.target_ckey]</b></font><br>"
	msg += "<b>Type:</b> <b>[BR.ban_type]</b> ([duration_text])<br>"
	if(BR.job)
		msg += "<b>Job(s):</b> [BR.job]<br>"
	msg += "<b>Reason:</b> [BR.reason]<br><br>"
	msg += "<a href='byond://?_src_=holder;approve_ban_req=[BR.id]'><b>\[APPROVE BAN\]</b></a> | "
	msg += "<a href='byond://?_src_=holder;deny_ban_req=[BR.id]'><b>\[DENY REQUEST\]</b></a> | "
	msg += "<a href='byond://?_src_=holder;shownoteckey=[BR.target_ckey]'><b>\[VIEW NOTES\]</b></a>"
	msg += "</div>"

	for(var/client/C in GLOB.admins)
		if(check_rights(R_BAN|R_ADMIN|R_MANAGEMENT, 0, C.mob))
			to_chat(C, msg, confidential = TRUE)
			SEND_SOUND(C, sound('sound/effects/adminhelp.ogg', volume = 75))

/client/proc/prompt_ban_request(default_ckey = null, mob/default_mob = null)
	if(!holder || !check_rights(R_MOD | R_CHIEF_MENTOR | R_BAN, FALSE))
		to_chat(src, SPAN_WARNING("You do not have permission to request bans."))
		return

	var/target_ckey = default_ckey
	if(!target_ckey)
		var/new_ckey = clean_input("Enter the ckey of the player to ban:","Ban Request", null)
		if(!new_ckey)
			return
		target_ckey = ckey(new_ckey)

	var/is_chief_mentor = check_rights(R_CHIEF_MENTOR, FALSE) && !check_rights(R_MOD|R_BAN, FALSE)
	var/list/type_options = list()
	if(is_chief_mentor)
		type_options = list(
			"Temp Server Ban",
			"Perma Server Ban",
			"Extended Temp Job Ban (>14 days)",
			"Perma Job Ban"
		)
	else
		type_options = list(
			"Extended Temp Server Ban (>14 days)",
			"Perma Server Ban",
			"Extended Temp Job Ban (>14 days)",
			"Perma Job Ban"
		)

	var/chosen_type = input(src, "Select the type of ban you are requesting:", "Ban Request Type") as null|anything in type_options
	if(!chosen_type)
		return

	var/duration = 0
	var/job = ""

	if(findtext(chosen_type, "Job Ban"))
		var/list/job_choices = get_all_jobs() + GLOB.nonhuman_positions + GLOB.other_roles + list("commanddept","securitydept","engineeringdept","medicaldept","sciencedept","servicedept","nonhumandept","All Jobs")
		job = input(src, "Select the department or job to ban from:", "Job Ban Selection") as null|anything in job_choices
		if(!job)
			return

	if(findtext(chosen_type, "Temp"))
		var/days = input(src, "Enter the requested duration in DAYS (e.g. 14, 30, 90):", "Ban Duration (Days)", 30) as num|null
		if(!days || days <= 0)
			return
		duration = days * 1440

	var/reason = input(src, "Please enter a detailed reason and context for this ban request:", "Ban Request Reason") as message|null
	if(!reason)
		return

	GLOB.ban_request_counter++
	var/datum/ban_request/BR = new()
	BR.id = GLOB.ban_request_counter
	BR.requester_ckey = ckey
	BR.requester_rank = holder.rank
	BR.target_ckey = target_ckey
	BR.ban_type = chosen_type
	BR.duration = duration
	BR.job = job
	BR.reason = reason
	BR.timestamp = world.realtime
	BR.status = "PENDING"

	GLOB.pending_ban_requests["[BR.id]"] = BR

	notify_admins_ban_request(BR)
	to_chat(src, SPAN_BOLDNOTICE("Your ban request for [target_ckey] ([chosen_type]) has been submitted to online Admins."))
	log_admin("[key_name(src)] submitted a ban request for [target_ckey]: [chosen_type] ([duration] mins) - [reason]")

USER_VERB(request_ban_approval, R_MOD|R_CHIEF_MENTOR|R_BAN, "Request Ban Approval", "Request an admin to approve a longer, job, or server ban.", VERB_CATEGORY_ADMIN)
	client.prompt_ban_request()

/proc/handle_ban_request_approval(mob/user, req_id)
	if(!check_rights(R_BAN|R_ADMIN, FALSE, user))
		to_chat(user, SPAN_WARNING("You do not have permission to approve bans."))
		return

	var/datum/ban_request/BR = GLOB.pending_ban_requests["[req_id]"]
	if(!BR)
		to_chat(user, SPAN_WARNING("Ban request #[req_id] not found or has already been resolved."))
		return
	if(BR.status != "PENDING")
		to_chat(user, SPAN_WARNING("Ban request #[req_id] has already been [lowertext(BR.status)] by [BR.handled_by]."))
		return

	var/confirm = alert(user, "Approve and apply [BR.ban_type] for [BR.target_ckey]?\nReason: [BR.reason]", "Confirm Ban Approval", "Approve", "Cancel")
	if(confirm != "Approve")
		return

	var/bantype
	if(findtext(BR.ban_type, "Perma Server"))
		bantype = BANTYPE_PERMA
	else if(findtext(BR.ban_type, "Temp Server"))
		bantype = BANTYPE_TEMP
	else if(findtext(BR.ban_type, "Perma Job"))
		bantype = BANTYPE_JOB_PERMA
	else if(findtext(BR.ban_type, "Temp Job"))
		bantype = BANTYPE_JOB_TEMP

	BR.status = "APPROVED"
	BR.handled_by = user.ckey
	GLOB.pending_ban_requests -= "[req_id]"

	user.client.holder.DB_ban_record(bantype, null, BR.duration, "[BR.reason] (Requested by [BR.requester_ckey])", BR.job, 0, BR.target_ckey)
	add_note(BR.target_ckey, "[BR.ban_type] approved by [user.ckey] (requested by [BR.requester_ckey]): [BR.reason]", null, user.ckey, FALSE)

	message_admins(SPAN_NOTICE("[key_name_admin(user)] approved [BR.requester_ckey]'s ban request for [BR.target_ckey] ([BR.ban_type])."))
	log_admin("[key_name(user)] approved [BR.requester_ckey]'s ban request for [BR.target_ckey] ([BR.ban_type])")

	var/client/req_client = GLOB.directory[BR.requester_ckey]
	if(req_client)
		to_chat(req_client, SPAN_BOLDNOTICE("Your ban request for [BR.target_ckey] was APPROVED by [user.ckey]."))

/proc/handle_ban_request_denial(mob/user, req_id)
	if(!check_rights(R_BAN|R_ADMIN, FALSE, user))
		to_chat(user, SPAN_WARNING("You do not have permission to deny bans."))
		return

	var/datum/ban_request/BR = GLOB.pending_ban_requests["[req_id]"]
	if(!BR)
		to_chat(user, SPAN_WARNING("Ban request #[req_id] not found or has already been resolved."))
		return
	if(BR.status != "PENDING")
		to_chat(user, SPAN_WARNING("Ban request #[req_id] has already been [lowertext(BR.status)] by [BR.handled_by]."))
		return

	var/deny_reason = input(user, "Reason for denying this request:", "Denial Reason", "Insufficient evidence / Not approved") as text|null
	if(!deny_reason)
		return

	BR.status = "DENIED"
	BR.handled_by = user.ckey
	GLOB.pending_ban_requests -= "[req_id]"

	message_admins(SPAN_NOTICE("[key_name_admin(user)] DENIED [BR.requester_ckey]'s ban request for [BR.target_ckey]. Reason: [deny_reason]"))
	log_admin("[key_name(user)] denied [BR.requester_ckey]'s ban request for [BR.target_ckey]. Reason: [deny_reason]")

	var/client/req_client = GLOB.directory[BR.requester_ckey]
	if(req_client)
		to_chat(req_client, SPAN_BOLDWARNING("Your ban request for [BR.target_ckey] was DENIED by [user.ckey]. Reason: [deny_reason]"))
