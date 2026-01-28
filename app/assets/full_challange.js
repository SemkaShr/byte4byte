async function invisibleReload() {
    const url = window.location.href;

    const response = await fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store'
    });

    const htmlText = await response.text();

    const parser = new DOMParser();
    const newDoc = parser.parseFromString(htmlText, 'text/html');

    document.head.innerHTML = '';

    Array.from(newDoc.head.children).forEach(node => {
        document.head.appendChild(node.cloneNode(true));
    });

    const scrollX = window.scrollX;
    const scrollY = window.scrollY;

    document.body.innerHTML = '';

    Array.from(newDoc.body.children).forEach(node => {
        document.body.appendChild(node.cloneNode(true));
    });

    window.scrollTo(scrollX, scrollY);

    const scripts = document.querySelectorAll('script');

    scripts.forEach(oldScript => {
        const newScript = document.createElement('script');

        Array.from(oldScript.attributes).forEach(attr => {
            newScript.setAttribute(attr.name, attr.value);
        });

        if (oldScript.textContent) {
            newScript.textContent = oldScript.textContent;
        }

        oldScript.replaceWith(newScript);
    });
}

(function() {
    function getBotVars() {
        const vars = [
            '__webdriver_evaluate', '__selenium_evaluate', '__webdriver_script_function',
            '__webdriver_script_func', '__webdriver_attributes', '__webdriver_unwrapped',
            '__fxdriver_unwrapped', '_phantom', '__nightmare', '_selenium', 'callPhantom',
            'callSelenium', '_Selenium_IDE_Recorder', 'domAutomation', 'domAutomationController',
            '__driver_evaluate', '__driver_unwrapped'
        ];
        const found = vars.filter(v => window[v] !== undefined || document[v] !== undefined);
        
        for (let key in window) {
            if (key.match(/\$cdc_|[a-z0-9]{22}_/i)) found.push("cd");
        }
        return found;
    };

    function getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = 300;
            canvas.height = 200;
            ctx.textBaseline = "top";
            ctx.font = "14px 'Arial'";
            ctx.textBaseline = "alphabetic";
            ctx.fillStyle = "#f60";
            ctx.fillRect(125, 1, 62, 200);
            ctx.fillStyle = "#069";
            ctx.fillText("byte4byte, <canvas> 1.0", 2, 15);
            ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
            ctx.fillText("b4b, <canvas> 1.0", 4, 17);
            return canvas.toDataURL();
        } catch (e) { return "error"; }
    }

    async function getBatteryInfo() {
        if (!navigator.getBattery) return "not_supported";
        try {
            const battery = await navigator.getBattery();
            return {
                '{{BATTERY_LEVEL}}': battery.level,
                '{{BATTERY_CHARGING}}': battery.charging,
                '{{BATTERY_CHARGING_TIME}}': battery.chargingTime
            };
        } catch (e) { return "error"; }
    }

    function getJitPerformance() {
        const start = performance.now();
        let val = 0;
        for (let i = 0; i < 2000000; i++) {
            val += Math.sqrt(i) * Math.sin(i);
        }
        const end = performance.now();
        return end - start;
    }

    function getFonts() {
        const fontList = ["Arial", "Courier New", "Georgia", "Times New Roman", "Verdana", "Impact", "Segoe UI"];
        const detected = [];
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");
        for (const font of fontList) {
            context.font = "72px monospace";
            const baselineSize = context.measureText("mmmmmmmmmmlli").width;
            context.font = "72px " + font + ", monospace";
            const newSize = context.measureText("mmmmmmmmmmlli").width;
            if (newSize !== baselineSize) detected.push(font);
        }
        return detected;
    }

    async function collectAllSignals() {
        const signals = {
            '{{WEBGL}}': (() => {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl');
                if (!gl) return null;
                const debug = gl.getExtension('WEBGL_debug_renderer_info');
                return {
                    '{{WEBGL_VENDOR}}': debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : 'unknown',
                    '{{WEBGL_RENDERER}}': debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : 'unknown'
                };
            })(),
            '{{CANVAS}}': getCanvasFingerprint(),
            '{{BATTERY}}': await getBatteryInfo(),
            '{{FONTS}}': getFonts(),
            '{{BOTVARS}}': getBotVars(),
            '{{JIT_PERFORMANCE}}': getJitPerformance(),
            '{{WEBDRIVER}}': navigator.webdriver,
            '{{PLUGINS}}': navigator.plugins.length,
            '{{LANGUAGES}}': navigator.languages,
            '{{IS_NATIVE_TO_STR}}': Function.prototype.toString.call(Function.prototype.toString).includes("[native code]"),
            '{{SCREEN_W}}': screen.width,
            '{{SCREEN_H}}': screen.height,
            '{{SCREEN_AW}}': screen.availWidth,
            '{{SCREEN_AH}}': screen.availHeight,
            '{{SCREEN_IW}}': window.innerWidth,
            '{{SCREEN_IH}}': window.innerHeight,
            '{{SCREEN_OW}}': window.outerWidth,
            '{{SCREEN_OH}}': window.outerHeight,
            '{{SCREEN_RATIO}}': window.devicePixelRatio,
            '{{CORES}}': navigator.hardwareConcurrency,
            '{{MEMORY}}': navigator.deviceMemory,
            '{{PLATFORM}}': navigator.platform
        };

        return signals;
    }

    async function encrypt(data) {
        const enc = new TextEncoder();
        const keyData = enc.encode("{{SCRIPT_KEY}}".slice(0, 32));
        const dataBytes = enc.encode(data);
        
        const cryptoKey = await crypto.subtle.importKey(
            "raw", keyData, { name: "AES-ECB" }, false, ["encrypt"]
        );
        
        const encrypted = await crypto.subtle.encrypt(
            { name: "AES-ECB" }, cryptoKey, dataBytes
        );
        
        return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
    }

    async function send() {
        data = await collectAllSignals();
        fetch("/{{SCRIPT_HASH_ID}}", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: encrypt(JSON.stringify(data))
        }).then(r => { invisibleReload() });
    }

    window.addEventListener('load', send);
})();