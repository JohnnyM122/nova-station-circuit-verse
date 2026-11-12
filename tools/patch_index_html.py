with open("cv_panel/index.html", "r", encoding="utf-8") as f:
    content = f.read()

target = """    async function loadPzMods() {
      try {
        const d = await api('/api/pz/mods');
        renderPzCatalog(d.curated_catalog || [], d.workshop_ids || []);
        const wids = d.workshop_ids || [];
        const mids = d.mod_ids || [];
        document.getElementById('pz-installed-mods-tbody').innerHTML = wids.length ? wids.map((w, i) => `
          <tr>
            <td>
              <a href="https://steamcommunity.com/sharedfiles/filedetails/?id=${w}" target="_blank" style="color:var(--accent); text-decoration:underline; font-weight:600;"><code>${w}</code> ↗</a>
            </td>
            <td><code>${mids[i] || '—'}</code></td>
            <td style="white-space:nowrap;">
              <button class="btn btn-secondary" style="padding:3px 7px; font-size:0.75rem;" onclick="pzMoveMod(${i}, -1)" ${i === 0 ? 'disabled' : ''}>▲</button>
              <button class="btn btn-secondary" style="padding:3px 7px; font-size:0.75rem;" onclick="pzMoveMod(${i}, 1)" ${i === wids.length - 1 ? 'disabled' : ''}>▼</button>
              <button class="btn btn-danger" style="padding:3px 7px; font-size:0.75rem; margin-left:4px;" onclick="pzRemoveMod('${w}','${mids[i] || ''}')">✖</button>
            </td>
          </tr>
        `).join('') : '<tr><td colspan="3" style="color:var(--muted); text-align:center; padding:16px;">No Workshop mods currently in CircuitVersePZ.ini (Vanilla Build 42)</td></tr>';

        const iniEditor = document.getElementById('pz-ini-editor');
        if (iniEditor && d.raw_ini) iniEditor.value = d.raw_ini;
        const sbEditor = document.getElementById('pz-sandbox-editor');
        if (sbEditor && d.raw_sandbox) sbEditor.value = d.raw_sandbox;
      } catch (e) {
        toast('Failed to load PZ Mods: ' + e.message);
      }
    }"""

replacement = """    async function loadPzMods() {
      try {
        const d = await api('/api/pz/mods');
        renderPzCatalog(d.curated_catalog || [], d.workshop_ids || []);
        const items = d.installed_items || [];
        document.getElementById('pz-installed-mods-tbody').innerHTML = items.length ? items.map((item, i) => `
          <tr>
            <td>
              <div style="font-weight:600; color:var(--text); font-size:0.86rem; margin-bottom:2px;">${item.title || ('Workshop #' + item.workshop_id)}</div>
              <a href="https://steamcommunity.com/sharedfiles/filedetails/?id=${item.workshop_id}" target="_blank" style="color:var(--accent); font-size:0.75rem; text-decoration:underline;"><code>${item.workshop_id}</code> ↗</a>
            </td>
            <td>
              ${(item.mod_ids && item.mod_ids.length) ? item.mod_ids.map(m => `<span style="display:inline-block; background:#1e293b; color:#38bdf8; border:1px solid rgba(56,189,248,0.25); border-radius:4px; padding:2px 6px; font-size:0.75rem; margin:2px 3px 2px 0; font-family:'JetBrains Mono',monospace;">${m}</span>`).join('') : '<span style="color:var(--muted); font-size:0.75rem;">(Pending Mod ID)</span>'}
              ${item.downloaded ? '<span style="display:inline-block; color:#4ade80; font-size:0.7rem; font-weight:600; margin-left:4px;">● Ready</span>' : '<span style="display:inline-block; color:#f59e0b; font-size:0.7rem; font-weight:600; margin-left:4px;">⏳ Downloading</span>'}
            </td>
            <td style="white-space:nowrap;">
              <button class="btn btn-secondary" style="padding:3px 7px; font-size:0.75rem;" onclick="pzMoveMod(${i}, -1)" ${i === 0 ? 'disabled' : ''}>▲</button>
              <button class="btn btn-secondary" style="padding:3px 7px; font-size:0.75rem;" onclick="pzMoveMod(${i}, 1)" ${i === items.length - 1 ? 'disabled' : ''}>▼</button>
              <button class="btn btn-danger" style="padding:3px 7px; font-size:0.75rem; margin-left:4px;" onclick="pzRemoveMod('${item.workshop_id}','${(item.mod_ids || []).join(';')}')">✖</button>
            </td>
          </tr>
        `).join('') : '<tr><td colspan="3" style="color:var(--muted); text-align:center; padding:16px;">No Workshop mods currently in CircuitVersePZ.ini (Vanilla Build 42)</td></tr>';

        const iniEditor = document.getElementById('pz-ini-editor');
        if (iniEditor && d.raw_ini) iniEditor.value = d.raw_ini;
        const sbEditor = document.getElementById('pz-sandbox-editor');
        if (sbEditor && d.raw_sandbox) sbEditor.value = d.raw_sandbox;
      } catch (e) {
        toast('Failed to load PZ Mods: ' + e.message);
      }
    }"""

if target in content:
    content = content.replace(target, replacement)
    print("Replaced loadPzMods successfully!")
else:
    print("Target not found!")

# Also update pzInstallModCustom
target_custom = """    async function pzInstallModCustom() {
      const wid = document.getElementById('pz-custom-wid').value.trim();
      const mid = document.getElementById('pz-custom-mid').value.trim();
      if (!wid || !mid) return toast('Enter both Workshop ID and Mod ID');
      await pzInstallMod(wid, mid);
    }"""

replacement_custom = """    async function pzInstallModCustom() {
      let wid = document.getElementById('pz-custom-wid').value.trim();
      let mid = document.getElementById('pz-custom-mid').value.trim();
      
      const urlMatch = wid.match(/[?&]id=(\\d+)/i) || wid.match(/\\/(\\d+)\\/?$/);
      if (urlMatch) wid = urlMatch[1];
      if (!wid) return toast('Please enter a Steam Workshop ID or URL');

      if (!mid) {
        const curated = (window._pzCuratedCatalog || []).find(c => String(c.workshop_id) === String(wid));
        if (curated) {
          mid = curated.mod_id;
        } else {
          mid = prompt('Enter the Mod ID for this Workshop item (e.g. Explosives, commonSense):') || '';
          mid = mid.trim();
          if (!mid) return toast('Mod ID is required for Project Zomboid to load the mod');
        }
      }
      await pzInstallMod(wid, mid);
    }"""

if target_custom in content:
    content = content.replace(target_custom, replacement_custom)
    print("Replaced pzInstallModCustom successfully!")
else:
    print("Target custom not found!")

with open("cv_panel/index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated index.html!")
