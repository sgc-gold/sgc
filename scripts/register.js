// register.js  --- for sgc-gold/sgc

const repoOwner = "sgc-gold";
const repoName = "sgc";
const filePath = "data/calibrations.json";

document.getElementById("submit").addEventListener("click", async () => {
  const token = document.getElementById("token").value.trim();
  if (!token) return alert("Tokenを入力してください。");

  const entry = {
    id: crypto.randomUUID(),
    date: new Date().toISOString(),
    stone: document.getElementById("stone").value,
    cut: document.getElementById("cut").value,
    diameter_mm: parseFloat(document.getElementById("diameter").value),
    height_mm: parseFloat(document.getElementById("height").value),
    measured_g: parseFloat(document.getElementById("measured").value)
  };

  const resultText = await addCalibrationToGitHub(token, entry);
  document.getElementById("result").innerText = resultText;
});

async function addCalibrationToGitHub(token, entry) {
  const url = `https://api.github.com/repos/${repoOwner}/${repoName}/contents/${filePath}`;
  const headers = {
    "Authorization": `token ${token}`,
    "Accept": "application/vnd.github.v3+json"
  };

  try {
    const res = await fetch(url, { headers });
    if (!res.ok) return "❌ ファイル取得エラー";
    const data = await res.json();

    // base64 → JSONデコード
    const content = atob(data.content);
    const json = JSON.parse(content || '{"calibrations": []}');
    json.calibrations.push(entry);

    // JSON → base64変換
    const updated = btoa(unescape(encodeURIComponent(JSON.stringify(json, null, 2))));

    // PUTで更新コミット
    const commitMsg = `Add calibration ${entry.id}`;
    const putRes = await fetch(url, {
      method: "PUT",
      headers,
      body: JSON.stringify({
        message: commitMsg,
        content: updated,
        sha: data.sha
      })
    });

    if (putRes.ok) {
      return "✅ 登録完了しました！（GitHubに保存されました）";
    } else {
      return "❌ 登録エラー: PUT失敗";
    }

  } catch (e) {
    console.error(e);
    return "⚠️ 通信またはJSON処理エラー";
  }
}
