const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];


export function formatTime(time) {
    if (!time) return '';
    const t = new Date(time * 1000)
    return `${months[t.getMonth()]} ${t.getDate()} ${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`
}