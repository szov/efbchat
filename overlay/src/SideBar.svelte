<script>
    import {formatTime} from "./lib/utils.js";

    let isOpen = $state(false)
    let {contacts, onSelect} = $props()
</script>

<button class="toggle-btn" class:hidden={isOpen} onclick={() => isOpen = !isOpen}>
    ☰
</button>

{#if isOpen}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="backdrop" onclick={() => isOpen = false}></div>
{/if}

<div class="sidebar" class:open={isOpen}>
    <div class="sidebar-header">
        <h2>Chats</h2>
        <button class="close-btn" onclick={() => isOpen = false}>✕</button>
    </div>
    <div class="sidebar-content">
        {#if contacts.length}
            {#each contacts as contact (contact.user_id)}
                <button class="contact-row" onclick={() => {onSelect(contact.user_id); isOpen = false; }}>
                    <div class="contact-header">
                        <span class="contact-name">{contact.username}</span>
                        <span class="contact-meta">{contact.match_count}
                            match{contact.match_count !== 1 ? 'es' : ''}</span>
                    </div>
                    <div class="contact-preview">
                        <span class="contact-msg">{contact.last_message?.slice(0, 40) || 'No messages yet'}</span>
                        <span class="contact-time">{formatTime(contact.last_ts)}</span>
                    </div>
                </button>
            {/each}
        {:else}
            <span class="contact-name">No chats yet.</span>
        {/if}

    </div>
</div>

<style>
    .toggle-btn {
        position: fixed;
        top: 5px;
        left: 5px;
        z-index: 101;
        background: rgba(6, 6, 18, 0.88);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text-muted);
        font-size: 14px;
        cursor: pointer;
        padding: 3px 8px;
        opacity: 0;
        transition: opacity 0.2s ease;
    }

    .toggle-btn:hover {
        opacity: 1;
    }

    .toggle-btn.hidden {
        opacity: 0;
        pointer-events: none;
    }

    .backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(2px);
        -webkit-backdrop-filter: blur(2px);
        z-index: 99;
    }

    .sidebar {
        position: fixed;
        top: 0;
        left: 0;
        width: 260px;
        height: 100vh;
        background: rgba(6, 6, 18, 0.92);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        z-index: 100;
        transform: translateX(-100%);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
    }

    .sidebar.open {
        transform: translateX(0);
    }

    .sidebar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 16px;
        box-shadow: 0 1px 0 var(--border);
    }

    .sidebar-header h2 {
        margin: 0;
        font-size: 13px;
        color: var(--text);
        font-weight: 600;
    }

    .close-btn {
        background: none;
        border: none;
        color: var(--text-muted);
        font-size: 14px;
        cursor: pointer;
        padding: 2px 6px;
        transition: color 0.15s ease;
    }

    .close-btn:hover {
        color: var(--text);
    }

    .sidebar-content {
        flex: 1;
        overflow-y: auto;
        padding: 4px 0;
    }

    .contact-row {
        display: flex;
        flex-direction: column;
        gap: 3px;
        width: 100%;
        padding: 12px 16px;
        border: none;
        box-shadow: 0 1px 0 var(--border);
        background: none;
        color: var(--text);
        cursor: pointer;
        text-align: left;
        transition: background 0.12s ease;
    }

    .contact-row:hover {
        background: rgba(124, 111, 247, 0.06);
    }

    .contact-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
    }

    .contact-name {
        font-size: 12px;
        font-weight: 600;
        color: var(--text);
    }

    .contact-meta {
        font-size: 9px;
        color: var(--text-muted);
        flex-shrink: 0;
    }

    .contact-preview {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 8px;
    }

    .contact-msg {
        font-size: 11px;
        color: var(--text-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        min-width: 0;
    }

    .contact-time {
        font-size: 9px;
        color: var(--text-muted);
        opacity: 0.5;
        flex-shrink: 0;
    }
</style>
