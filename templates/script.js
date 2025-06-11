document.getElementById('ask-form').onsubmit = async function(e) {
  e.preventDefault();
  const message = document.getElementById('message').value;
  document.getElementById('response').textContent = "Loading...";

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ message })
    });

    const data = await res.json();
    document.getElementById('response').textContent = data.response;
  } catch (err) {
    document.getElementById('response').textContent = "There was an error contacting the AI.";
    console.error(err);
  }
};
