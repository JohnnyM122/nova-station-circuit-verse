/proc/fix_station_breaches_and_equipment(client/user)
	if(user && !check_rights_client(R_ADMIN | R_BUILDMODE, TRUE, user, all = TRUE))
		return

	if(user)
		var/confirm = tgui_alert(user, "Are you sure you want to fix and reset all station breaches, damaged structures, windows, doors, and equipment?", "Confirm Station Repair", list("Yes", "No"))
		if(confirm != "Yes")
			return

	message_admins(SPAN_NOTICE("[key_name_admin(user ? user : usr)] initiated a full station repair and breach reset."))
	log_admin("[key_name(user ? user : usr)] initiated full station repair.")

	var/turfs_fixed = 0
	var/walls_fixed = 0
	var/windows_fixed = 0
	var/doors_fixed = 0

	// 1. Repair APCs and restore station power
	power_restore(FALSE, 2)

	// 2. Iterate station turfs across all levels
	for(var/z = 1 to world.maxz)
		if(!is_station_level(z))
			continue
		for(var/x = 1 to world.maxx)
			for(var/y = 1 to world.maxy)
				var/turf/T = locate(x, y, z)
				if(!T)
					continue
				var/area/A = T.loc
				if(!A || istype(A, /area/space))
					continue

				// Station area turf! Check for breaches (space or airless plating in station area)
				if(isspaceturf(T))
					T.ChangeTurf(/turf/simulated/floor/plating)
					turfs_fixed++
				else if(istype(T, /turf/simulated/floor/plating/airless))
					T.ChangeTurf(/turf/simulated/floor/plating)
					turfs_fixed++

				// Fix damaged walls
				if(istype(T, /turf/simulated/wall))
					var/turf/simulated/wall/W = T
					if(W.damage > 0)
						W.damage = 0
						W.update_icon()
						walls_fixed++

				// Fix contents on this turf
				for(var/atom/movable/AM in T)
					// Fix damaged windows
					if(istype(AM, /obj/structure/window))
						var/obj/structure/window/Win = AM
						if(Win.obj_integrity < Win.max_integrity)
							Win.obj_integrity = Win.max_integrity
							Win.update_icon()
							windows_fixed++
					// Fix damaged airlocks
					else if(istype(AM, /obj/machinery/door/airlock))
						var/obj/machinery/door/airlock/AL = AM
						if(AL.obj_integrity < AL.max_integrity || AL.welded)
							AL.obj_integrity = AL.max_integrity
							AL.welded = FALSE
							AL.locked = FALSE
							AL.update_icon()
							doors_fixed++

	message_admins(SPAN_NOTICE("Station repair complete: [turfs_fixed] breached turfs sealed, [walls_fixed] walls restored, [windows_fixed] windows repaired, [doors_fixed] airlocks repaired."))

USER_VERB(repair_station_all, R_ADMIN | R_BUILDMODE, "Fix / Reset Station", "Repairs all station breaches, damaged floors, walls, windows, airlocks, and restores power/atmosphere on the station", VERB_CATEGORY_ADMIN)
	if(!check_rights_client(R_ADMIN | R_BUILDMODE, TRUE, client, all = TRUE))
		return
	fix_station_breaches_and_equipment(client)
