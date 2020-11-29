
export function fmtEpochTime(ms_time) {

    const dt = new Date(ms_time)

    let d = dt.getDate()
    let m = dt.getMonth()+1
    let y = dt.getFullYear()
    let H = dt.getHours()
    let M = dt.getMinutes()
    let S = dt.getSeconds()
    let Z = dt.getTimezoneOffset()
    let zh = -Math.floor(Z / 60)
    let zm = Math.abs(Z) % 60
    if (zm < 9) {
        zm = '0' + zm;
    }
    return `${y}/${m}/${d} ${H}:${M}:${S} ${zh}:${zm}`

}