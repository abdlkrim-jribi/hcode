/* Hcode Interactive Scripts */

document.addEventListener('DOMContentLoaded', () => {
    initTerminal();
    initScrollAnimations();
    initGlitchEffect();
});

/* --- Terminal Typing Effect --- */
const terminalLines = [
    { text: 'hcode planning --goal "build a modern website"', class: 'command' },
    { text: 'Thinking Process:', class: 'info' },
    { text: '  - Cognitive Layer: Analyzing request requirements...', class: 'dim' },
    { text: '  - Memory Layer: Retrieving project context...', class: 'dim' },
    { text: '  - Strategy: Use HTML5, CSS Grid, and Glassmorphism.', class: 'dim' },
    { text: 'Executing Phase 1: Structure Setup...', class: 'success' },
    { text: '  > mkdir docs/website', class: 'text-main' },
    { text: '  > touch index.html style.css', class: 'text-main' },
    { text: 'Executing Phase 2: Design Implementation...', class: 'success' },
    { text: '  > Applying dark mode theme...', class: 'dim' },
    { text: '  > Adding interactive elements...', class: 'dim' },
    { text: 'Verify Phase: Website build complete.', class: 'success' },
    { text: 'Ready for deployment. 🚀', class: 'highlight' }
];

async function initTerminal() {
    const terminalBody = document.querySelector('.terminal-body');
    if (!terminalBody) return;

    // Clear existing content
    terminalBody.innerHTML = '';

    for (const line of terminalLines) {
        await typeLine(line, terminalBody);
    }

    // Add final cursor
    const cursor = document.createElement('div');
    cursor.className = 'output-line';
    cursor.innerHTML = '<span class="prompt">➜</span> <span class="typing-cursor"></span>';
    terminalBody.appendChild(cursor);
}

function typeLine(lineData, container) {
    return new Promise(resolve => {
        const line = document.createElement('div');
        line.className = `output-line ${lineData.class || ''}`;

        // Add prompt if it's a command
        if (lineData.class === 'command') {
            const prompt = document.createElement('span');
            prompt.className = 'prompt';
            prompt.textContent = '➜ ';
            line.appendChild(prompt);
        }

        container.appendChild(line);

        let text = lineData.text;
        let i = 0;
        const speed = 20; // typing speed in ms

        function typeChar() {
            if (i < text.length) {
                line.append(text.charAt(i));
                i++;
                setTimeout(typeChar, speed);
            } else {
                resolve();
            }
        }

        typeChar();
    });
}

/* --- Scroll Animations --- */
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, observerOptions);

    // Observe steps
    document.querySelectorAll('.step').forEach(el => observer.observe(el));

    // Observe feature cards
    document.querySelectorAll('.feature-card').forEach((el, index) => {
        el.style.transitionDelay = `${index * 100}ms`;
        observer.observe(el);
    });
}

/* --- Glitch Effect on Logo --- */
function initGlitchEffect() {
    const logo = document.querySelector('.logo');
    if (!logo) return;

    logo.addEventListener('mouseover', () => {
        logo.style.textShadow = '2px 0 var(--primary), -2px 0 var(--accent)';
        setTimeout(() => {
            logo.style.textShadow = 'none';
        }, 200);
    });
}
