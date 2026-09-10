<script>
    import {invoke} from '@tauri-apps/api/core';
    import {onMount} from 'svelte';
    import {connect, setCache, view} from './lib/ws.js'
    import ChatView from './ChatView.svelte'
    import SideBar from "./SideBar.svelte";

    let device_id = $state("");
    let contacts = $state([])

    // When the App first runs, this runs ONCE
    onMount(async () => {
        try {
            // call load_device_id() from (tauri) backend
            device_id = await invoke('load_device_id');
        } catch {
            // If running via browser, get it thru the localStorage
            device_id = localStorage.getItem("device_id");
            if (!device_id) {
                device_id = crypto.randomUUID();
                localStorage.setItem("device_id", device_id);
            }
        }

        // Connect to the /ws endpoint
        connect(device_id);

        try {
            const rect = JSON.parse(await invoke('get_game_rect'));
            if (rect && rect.w > 0) {
                await invoke('set_window_position', {
                    x: rect.x + rect.w - 410,
                    y: rect.y + 10,
                });
            }
        } catch {
            // eFootball not running — let OS place the window
        }

        try {
            const res = await fetch(`http://localhost:8000/contacts?device_id=${device_id}`)
            contacts = await res.json()
        } catch {

        }


    });

    /**
     * Load user chat history with a specific user
     * */
    async function loadHistory(partnerId) {
        try {
            const res = await fetch(`http://localhost:8000/history?device_id=${device_id}&partner_id=${partnerId}`);
            const history = await res.json();
            setCache(partnerId, history)
            view.set(partnerId)

        } catch (e) {
            // Low it
        }

    }
</script>

{#if device_id}
    <ChatView {device_id}/>
    <SideBar {contacts} onSelect={loadHistory}/>
{/if}
