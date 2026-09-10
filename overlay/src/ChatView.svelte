<script>
    import {flash, messages, sendMessage, status, view} from './lib/ws.js'
    import {formatTime} from "./lib/utils.js";

    let {device_id} = $props();

    let inputText = $state("");
    let hovered = $state(false);
    let locked = $state(false);
    let inputEl = $state(null)

    $effect(() => {
        if ((hovered || locked) && inputEl) {
            inputEl.focus()
        }
    })

    $effect(() => {
        if ($flash) locked = true
    });

    $effect(() => {
        requestAnimationFrame(() => {
            const container = document.getElementById('message-list')
            if (container) {
                container.scrollTop = container.scrollHeight
            }
        })
    })


    function handleSubmit(e) {
        e.preventDefault();
        if (!inputText.trim()) return;
        sendMessage(inputText);
        inputText = "";
    }

    function backToLive() {
        view.set("live")
    }

</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="overlay" class:expanded={hovered || locked} class:flash={$flash}
     onmouseenter={() => { hovered = true; }}
     onmouseleave={() => { hovered = false; }}>

    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <header class="status-bar" data-tauri-drag-region>
        <div class="status-row">
            {#if $status === "waiting"}
                <span class="status searching">Searching for opponent...</span>
            {:else if $status === "matched"}
                <span class="status matched">Connected</span>
            {:else if $status === "opponent_reconnecting"}
                <span class="status matched">Opponent reconnecting...</span>
            {:else if $status === "reconnecting"}
                <span class="status disconnected">Reconnecting...</span>
            {:else if $status === "disconnected"}
                <span class="status disconnected">Disconnected</span>
            {:else}
                <span class="status">Connecting...</span>
            {/if}

            {#if $view && $view !== "live"}
                <span class="status-subtitle">Viewing past chat</span>
                {#if $status === "matched" || $status === "opponent_reconnecting"}
                    <button class="back-to-live-btn" onclick={(e) => { e.stopPropagation(); backToLive(); }}>Back to
                        live
                    </button>
                {/if}
            {/if}
        </div>

        <div class="header-actions">
            <button class="lock-toggle" class:active={locked} onclick={() => locked = !locked} title="Pin overlay">
                <span class="knob"></span>
            </button>
        </div>
    </header>

    <div class="message-list" id="message-list">
        {#each $messages as msg (msg.id)}
            <div class="message" class:you={msg.sender === "You"} class:opponent={msg.sender !== "You"}>
                <span class="sender">{msg.sender}</span>
                <span class="content">{msg.content}</span>
                <span class="timestamp">{formatTime(msg.ts)}</span>
            </div>
        {/each}
    </div>

    {#if $view && $view === "live"}
        <footer class="input-bar" class:visible={hovered || locked}>
            <form onsubmit={handleSubmit}>
                <input type="text" bind:value={inputText} bind:this={inputEl} placeholder="Type a message..."/>
                <button type="submit">Send</button>
            </form>
        </footer>
    {/if}
</div>

<style>
    .overlay {
        display: flex;
        flex-direction: column;
        height: 28px;
        overflow: hidden;
        background: transparent;
        border: none;
        transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1), background 0.35s ease;
    }

    .overlay.expanded,
    .overlay.flash {
        height: 100vh;
        background: rgba(6, 6, 18, 0.88);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }

    .status-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 5px 14px;
        font-size: 11px;
        flex-shrink: 0;
        box-shadow: none;
        transition: box-shadow 0.35s ease;
    }

    .overlay.expanded .status-bar,
    .overlay.flash .status-bar {
        box-shadow: 0 1px 0 var(--border);
    }

    .status-row {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1px;
        flex: 1;
    }

    .status-subtitle {
        font-size: 10px;
        color: var(--text-muted);
    }

    .back-to-live-btn {
        background: none;
        border: none;
        color: var(--accent);
        font-size: 10px;
        cursor: pointer;
        padding: 1px 6px;
        opacity: 0.7;
        transition: opacity 0.15s ease;
    }

    .back-to-live-btn:hover {
        opacity: 1;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
    }

    .lock-toggle {
        width: 28px;
        height: 16px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.1);
        border: none;
        cursor: pointer;
        position: relative;
        transition: background 0.2s ease;
        flex-shrink: 0;
    }

    .lock-toggle.active {
        background: var(--accent);
    }

    .lock-toggle .knob {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: white;
        position: absolute;
        top: 2px;
        left: 2px;
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .lock-toggle.active .knob {
        transform: translateX(12px);
    }

    .status.searching { color: var(--accent); }
    .status.matched { color: var(--success); }
    .status.disconnected { color: var(--danger); }

    .message-list {
        flex: 1;
        overflow-y: auto;
        padding: 8px 10px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        opacity: 0;
        transition: opacity 0.25s ease;
    }

    .overlay.expanded .message-list,
    .overlay.flash .message-list {
        opacity: 1;
    }

    .message {
        padding: 8px 12px;
        border-radius: 12px;
        max-width: 80%;
        line-height: 1.4;
    }

    .message.you {
        background: rgba(124, 111, 247, 0.1);
        align-self: flex-end;
        border-bottom-right-radius: 6px;
    }

    .message.opponent {
        background: rgba(255, 255, 255, 0.04);
        align-self: flex-start;
        border-bottom-left-radius: 6px;
    }

    .message .sender {
        display: block;
        font-size: 10px;
        font-weight: 600;
        color: var(--text-muted);
        margin-bottom: 1px;
    }

    .message .content {
        font-size: 13px;
    }

    .message .timestamp {
        display: block;
        text-align: right;
        font-size: 9px;
        color: var(--text-muted);
        opacity: 0.4;
        margin-top: 4px;
    }

    .input-bar {
        padding: 8px 10px 10px;
        opacity: 0;
        transition: opacity 0.2s ease;
        pointer-events: none;
    }

    .overlay.expanded .input-bar,
    .overlay.flash .input-bar {
        border-top: none;
        box-shadow: 0 -1px 0 var(--border);
    }

    .input-bar.visible {
        opacity: 1;
        pointer-events: auto;
    }

    .input-bar form {
        display: flex;
        gap: 8px;
    }

    .input-bar input {
        flex: 1;
        padding: 9px 14px;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.04);
        color: var(--text);
        font-size: 13px;
        transition: border-color 0.15s ease, background 0.15s ease;
    }

    .input-bar input::placeholder {
        color: var(--text-muted);
        opacity: 0.4;
    }

    .input-bar input:focus {
        outline: none;
        border-color: var(--accent);
        background: rgba(255, 255, 255, 0.06);
    }

    .input-bar button {
        padding: 9px 16px;
        border: none;
        border-radius: 10px;
        background: var(--accent);
        color: white;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.12s ease;
    }

    .input-bar button:hover {
        opacity: 0.82;
    }
</style>
