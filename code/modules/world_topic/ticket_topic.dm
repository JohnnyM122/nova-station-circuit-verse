#ifndef TICKET_OPEN
#define TICKET_OPEN 1
#define TICKET_CLOSED 2
#define TICKET_RESOLVED 3
#define TICKET_STALE 4
#endif

/datum/world_topic_handler/ticket
	topic_key = "ticket"
	requires_commskey = TRUE

/datum/world_topic_handler/ticket/execute(list/input, key_valid)
	/*
	Handles ticket management from Discord bot.
	Expected parameters:
		action: "reply", "claim", "resolve", "close", "list"
		system: "admin" or "mentor" (defaults to "admin")
		id: ticket number (numeric)
		sender: Discord username or tag
		msg: message content (for reply)
	*/
	var/action = input["action"]
	var/system_type = input["system"] ? lowertext(input["system"]) : "admin"
	var/datum/controller/subsystem/tickets/ticket_system = (system_type == "mentor") ? SSmentor_tickets : SStickets

	if(!ticket_system)
		return json_encode(list("error" = "Ticket subsystem not available"))

	if(action == "list")
		var/list/active_tickets = list()
		for(var/N in ticket_system.allTickets)
			var/datum/ticket/T = ticket_system.allTickets[N]
			if(!T)
				continue
			var/list/ticket_info = list(
				"id" = T.ticketNum,
				"system" = system_type,
				"ckey" = T.client_ckey,
				"title" = T.title,
				"state" = T.ticketState,
				"staff" = T.staff_ckey ? T.staff_ckey : "Unassigned",
				"time" = T.real_time_opened
			)
			active_tickets += list(ticket_info)
		return json_encode(list("success" = TRUE, "tickets" = active_tickets))

	var/ticket_id = text2num(input["id"])
	if(!ticket_id || !ticket_system.allTickets[ticket_id])
		return json_encode(list("error" = "Ticket #[input["id"]] not found"))

	var/datum/ticket/T = ticket_system.allTickets[ticket_id]
	var/sender = sanitize(input["sender"])
	if(!sender)
		sender = "Discord Staff"

	switch(action)
		if("claim")
			T.staff_ckey = "[sender] (Discord)"
			T.staff_take_time = SQLtime()
			ticket_system.message_staff("<span class='[ticket_system.span_class]'><b>[sender] (Discord)</b> has claimed [ticket_system.ticket_name] #[T.ticketNum]</span>")
			ticket_system.refresh_tickets(list(T))
			return json_encode(list("success" = TRUE, "action" = "claim", "id" = T.ticketNum))

		if("reply")
			var/raw_msg = input["msg"]
			if(!raw_msg)
				return json_encode(list("error" = "No message provided"))
			var/sanitized_msg = sanitize(raw_msg)
			T.ticket_responses += new /datum/ticket_response(sanitized_msg, "[sender] (Discord)")
			T.lastStaffResponse = "[sender] (Discord)"
			T.lastResponseTime = SQLtime()

			var/client/C = ticket_system.returnClient(ticket_id)
			if(C)
				SEND_SOUND(C, sound('sound/effects/adminhelp.ogg'))
				to_chat(C, "<span class='[ticket_system.span_class]'><b>[ticket_system.ticket_name] PM from [sender] (Discord):</b> [sanitized_msg]</span>", MESSAGE_TYPE_ADMINPM)
			ticket_system.message_staff("<span class='[ticket_system.span_class]'><b>Discord PM from [sender] to [T.client_ckey] (Ticket #[T.ticketNum]):</b> [sanitized_msg]</span>")
			ticket_system.refresh_tickets(list(T))
			return json_encode(list("success" = TRUE, "action" = "reply", "id" = T.ticketNum))

		if("resolve")
			if(T.ticketState != TICKET_RESOLVED)
				T.ticketState = TICKET_RESOLVED
				ticket_system.message_staff("<span class='[ticket_system.span_class]'><b>[sender] (Discord)</b> resolved [ticket_system.ticket_name] #[T.ticketNum]</span>")
				ticket_system.sendFollowupToDiscord(T, "[sender] (Discord)", "*Ticket resolved.*")
				ticket_system.to_chat_safe(ticket_system.returnClient(ticket_id), "<span class='[ticket_system.span_class]'>Your [ticket_system.ticket_name] has now been resolved.</span>")
				ticket_system.open_ticket_count_updated()
				ticket_system.refresh_tickets(list(T))
			return json_encode(list("success" = TRUE, "action" = "resolve", "id" = T.ticketNum))

		if("close")
			if(T.ticketState != TICKET_CLOSED)
				T.ticketState = TICKET_CLOSED
				ticket_system.message_staff("<span class='[ticket_system.span_class]'><b>[sender] (Discord)</b> closed [ticket_system.ticket_name] #[T.ticketNum]</span>")
				ticket_system.sendFollowupToDiscord(T, "[sender] (Discord)", "*Ticket closed.*")
				ticket_system.to_chat_safe(ticket_system.returnClient(ticket_id), ticket_system.close_messages)
				ticket_system.open_ticket_count_updated()
				ticket_system.refresh_tickets(list(T))
			return json_encode(list("success" = TRUE, "action" = "close", "id" = T.ticketNum))

		else
			return json_encode(list("error" = "Unknown action: [action]"))
