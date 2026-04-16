async function loadData() {
    let res = await fetch('/api');
    let data = await res.json();

    document.getElementById("status").innerText = data.status;
    document.getElementById("players").innerText = data.players;
    document.getElementById("ip_show").innerText = data.ip;
}

async function setIP() {
    let ip = document.getElementById("ip").value;

    await fetch('/set_ip', {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ip})
    });

    alert("Saved!");
}

setInterval(loadData, 3000);
loadData();