function showTab(tab) {
    document.querySelectorAll(".tab").forEach(t => t.style.display = "none");
    document.getElementById(tab).style.display = "block";
}

async function loadData() {
    let res = await fetch('/api');
    let data = await res.json();

    document.getElementById("status").innerText = data.status;
    document.getElementById("players").innerText = data.players;
}

async function sendAction(action) {
    await fetch('/action', {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({action})
    });
}

async function loadConsole() {
    let res = await fetch('/console');
    let data = await res.json();
    document.getElementById("console").innerText = data.logs;
}

async function askAI() {
    let q = document.getElementById("ai_input").value;

    let res = await fetch('/ai', {
        method:"POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({q})
    });

    let data = await res.json();
    document.getElementById("ai_output").innerText = data.reply;
}

setInterval(loadData, 3000);
setInterval(loadConsole, 2000);

loadData();
loadConsole();
