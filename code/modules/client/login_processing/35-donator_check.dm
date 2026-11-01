/datum/client_login_processor/donator_check
	priority = 35
/// Reads the server-managed donator list (ckey,level) from config/donators.txt.
/proc/load_donator_levels()
	var/list/donator_levels = list()
	for(var/line in file2list("config/donators.txt"))
		line = trim(line)
		if(!line || copytext(line, 1, 2) == "#" || copytext(line, 1, 3) == "//")
			continue
		var/list/parts = splittext(line, ",")
		if(length(parts) != 2)
			continue
		var/donor_ckey = ckey(trim(parts[1]))
		var/level = text2num(trim(parts[2]))
		if(!donor_ckey || !isnum(level) || level < 1 || level > DONATOR_LEVEL_MAX || level != round(level))
			continue
		donator_levels[donor_ckey] = level
	return donator_levels

/datum/client_login_processor/donator_check/get_query(client/C)
	var/datum/db_query/query = SSdbcore.NewQuery("SELECT ckey, tier, active FROM donators WHERE ckey=:ckey", list(
		"ckey" = C.ckey
	))
	return query

/datum/client_login_processor/donator_check/process_result(datum/db_query/Q, client/C)
	if(IsGuestKey(C.key))
		return

	// Admins get all donor perks
	if(check_rights_client(R_ADMIN, FALSE, C))
		C.donator_level = DONATOR_LEVEL_MAX
		C.donor_loadout_points()
		return

	var/list/configured_donators = load_donator_levels()
	if(configured_donators[C.ckey])
		// The text file takes precedence over the legacy database tier.
		C.donator_level = configured_donators[C.ckey]
		C.donor_loadout_points()
		return
	while(Q.NextRow())
		if(!text2num(Q.item[3]))
			// Inactive donator.
			C.donator_level = 0
			return

		C.donator_level = text2num(Q.item[2])
		C.donor_loadout_points()
