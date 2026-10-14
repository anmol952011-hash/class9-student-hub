console.log("Script.js loaded successfully!")
;// Function to handle Summariser
document.getElementById('btn-summarize').addEventListener('click', async () => {
    // Get the text from the textarea
    const text = document.getElementById('summary-input').value;
    const outputDiv = document.getElementById('summary-output');
    const btn = document.getElementById('btn-summarize');

    if (!text) return alert("Please paste some text to summarize.");

    outputDiv.classList.remove('hidden');
    outputDiv.innerText = "⏳ Generating summary, please wait...";
    btn.disabled = true;

    try {
        const response = await fetch('/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // Send text instead of topic
            body: JSON.stringify({ text: text }) 
        });
        const data = await response.json();
        
        if (response.ok) {
            outputDiv.textContent = data.result;
        } else {
            outputDiv.innerText = "Backend Error: " + (data.error || "Unknown error");
        }
    } catch (error) {
        outputDiv.innerText = "Network Error: Could not reach the Python server.";
    } finally {
        btn.disabled = false;
    }
});
// Function to handle Mock Test
document.getElementById('btn-mocktest').addEventListener('click', async () => {
    const topic = document.getElementById('mocktest-input').value;
    const outputDiv = document.getElementById('mocktest-output');
    const btn = document.getElementById('btn-mocktest');

    if (!topic) return alert("Please enter a topic.");

    outputDiv.classList.remove('hidden');
    outputDiv.innerText = "⏳ Generating mock test, please wait...";
    btn.disabled = true;

    try {
        const response = await fetch('/api/mocktest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic })
        });
        const data = await response.json();
        outputDiv.innerText = data.result || data.error;
    } catch (error) {
        outputDiv.innerText = "Error connecting to the server.";
    } finally {
        btn.disabled = false;
    }
});

// Function to handle Q&A
document.getElementById('btn-ask').addEventListener('click', async () => {
    const question = document.getElementById('question-input').value;
    const outputDiv = document.getElementById('question-output');
    const btn = document.getElementById('btn-ask');

    if (!question) return alert("Please type a question.");

    outputDiv.classList.remove('hidden');
    outputDiv.innerText = "⏳ Searching knowledge base...";
    btn.disabled = true;

    // If it takes more than 1.5 seconds, update the text to let them know it's calling the AI
    const timer = setTimeout(() => {
        outputDiv.innerText = "this may take a few seconds...";
    }, 1500);

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });
        
        clearTimeout(timer); // Stop the timer because we got a response
        
        const data = await response.json();
        
        if (response.ok) {
            outputDiv.innerText = data.result;
        } else {
            outputDiv.innerText = "Backend Error: " + (data.error || "Unknown error");
        }
        
    } catch (error) {
        clearTimeout(timer);
        outputDiv.innerText = "Network Error: Could not reach the Python server.";
    } finally {
        btn.disabled = false;
    }
});