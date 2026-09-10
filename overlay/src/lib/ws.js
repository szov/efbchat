import {derived, get, writable} from 'svelte/store'
export const status = writable("disconnected")
export const matchId = writable(null)
export const flash = writable(false)
export const view = writable(null)

const chatCache = writable({})

export const messages = derived([chatCache, view], ([cache, currentView]) => {
    return currentView ? (cache[currentView] || []) : []
})

export function setCache(slot, msgs) {
    chatCache.update(c => ({...c, [slot]: msgs}))
}

let ws = null
let flashTimer = null
let retryInterval = null
let retryDeviceId = null







export function connect(deviceId) {
    retryDeviceId = deviceId
    ws = new WebSocket(`ws://localhost:8000/ws?device_id=${deviceId}`)

    status.set("connecting")

    ws.onopen = () => {
        status.set('connected')
        if (retryInterval) {
            clearInterval(retryInterval)
            retryInterval = null
        }
    }
    ws.onclose = () => {
        if (retryInterval) {
            status.set('reconnecting')
            return
        }

        status.set('reconnecting')
        let attempts = 0
        retryInterval = setInterval(() => {
            attempts++
            if (attempts > 5) {
                clearInterval(retryInterval)
                retryInterval = null
                status.set('disconnected')
                view.set(null)
                chatCache.set({})
                return
            }
            connect(retryDeviceId)
        }, 3000)
    }

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data)

        switch (data.type) {
            case "paired":
                matchId.set(data.matchId)
                status.set("matched")
                setCache("live", [])
                view.set("live")
                break
            case "waiting":
                status.set("waiting")
                break
            case "history":
                setCache("live", data.messages)
                break
            case "chat":
                chatCache.update(c => {
                    const live = [...(c["live"] || []), {
                        sender: data.sender,
                        content: data.content,
                        id: data.id,
                        ts: data.ts,
                    }]
                    return {...c, "live": live}
                })
                flash.set(true)

                clearTimeout(flashTimer)
                flashTimer = setTimeout(() => flash.set(false), 3000)
                break
            case "disconnected":
                status.set("disconnected")
                view.set(null)
                chatCache.set({})
                break
            case "opponent_reconnecting":
                status.set("opponent_reconnecting")
                break
            case "opponent_reconnected":
                status.set("matched")
                break
        }
    }
}

export function sendMessage(content) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(content)
    }
}
