(async()=>{ 
    async function encrypt(data){
        const enc=new TextEncoder();
        const keyStr="{{SCRIPT_KEY}}".slice(0,32);
        const keyData=enc.encode(keyStr);
        const cryptoKey=await crypto.subtle.importKey("raw",keyData,{name:"AES-CBC"},false,["encrypt"]);
        const dataBytes=enc.encode(data);
        const encrypted=await crypto.subtle.encrypt({name:"AES-CBC",iv:new Uint8Array(16)},cryptoKey,dataBytes);
        return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
    }

    const ENDPOINT="{{SCRIPT_ENDPOINT}}";
    const BATCH_INTERVAL=4000;
    const throttleMs=100;

    let startTs=Date.now();
    let lastActiveStart=Date.now();
    let hiddenStart=null;
    let hiddenTotal=0;
    let focusCount=0;
    let firstInteractionDelay=null;

    let mouse={
        lastX:null,lastY:null,lastT:0,
        moveCount:0,totalDist:0,sumSpeed:0,sumSpeedSq:0
    };
    let clicks={count:0,lastClickT:null,interDelays:[]};
    let scrolls={count:0,maxDepth:0,totalDelta:0,lastT:0,sumSpeed:0};
    let keys={count:0,dwellCount:0,sumDwell:0};
    let keyDownT=null;

    function now(){return Date.now();}

    function recordFirstInteraction(){ if(firstInteractionDelay===null) firstInteractionDelay=(now()-startTs)/1000; }

    let lastMouseEvent=0;
    window.addEventListener("mousemove",e=>{
        const t=now();
        if(t-lastMouseEvent<throttleMs) return;
        lastMouseEvent=t;
        recordFirstInteraction();
        const x=e.clientX,y=e.clientY;
        if(mouse.lastX!==null){
            const dx=x-mouse.lastX,dy=y-mouse.lastY;
            const dist=Math.hypot(dx,dy);
            const dt=(t-mouse.lastT)||1;
            const speed=dist/dt;
            mouse.moveCount++;
            mouse.totalDist+=dist;
            mouse.sumSpeed+=speed;
            mouse.sumSpeedSq+=speed*speed;
        }
        mouse.lastX=x;mouse.lastY=y;mouse.lastT=t;
    });

    window.addEventListener("mousedown",e=>{
        const t=now();
        recordFirstInteraction();
        clicks.count++;
        if(clicks.lastClickT) clicks.interDelays.push((t-clicks.lastClickT)/1000);
        clicks.lastClickT=t;
    });

    let lastScrollEvent=0;
    window.addEventListener("scroll",e=>{
        const t=now();
        if(t-lastScrollEvent<throttleMs) return;
        lastScrollEvent=t;
        recordFirstInteraction();
        const depth=Math.max(document.documentElement.scrollTop||document.body.scrollTop||0, window.scrollY||0);
        scrolls.count++;
        scrolls.maxDepth=Math.max(scrolls.maxDepth,depth);
        const delta= Math.abs((window.scrollY||depth)-(scrolls.lastDepth||0));
        const dt=(t-scrolls.lastT)||1;
        scrolls.totalDelta+=delta;
        scrolls.sumSpeed+=delta/dt;
        scrolls.lastDepth=window.scrollY||depth;
        scrolls.lastT=t;
    },{passive:true});

    window.addEventListener("keydown",e=>{
        recordFirstInteraction();
        if(keyDownT===null) keyDownT=now();
        keys.count++;
    });
    window.addEventListener("keyup",e=>{
        recordFirstInteraction();
        if(keyDownT!==null){
            const d=(now()-keyDownT)/1000;
            keys.dwellCount++; keys.sumDwell+=d;
            keyDownT=null;
        }
    });

    window.addEventListener("focus",()=>{ focusCount++; lastActiveStart=now(); });
    window.addEventListener("blur",()=>{ if(lastActiveStart){ hiddenTotal+=now()-lastActiveStart; lastActiveStart=null; } });

    document.addEventListener("visibilitychange",()=>{
        if(document.visibilityState==="hidden"){ hiddenStart=now(); if(lastActiveStart){ hiddenTotal+=now()-lastActiveStart; lastActiveStart=null; } }
        else { if(hiddenStart){ hiddenTotal+=0; hiddenStart=null; } if(!lastActiveStart) lastActiveStart=now(); }
    });

    function assembleFeatures(){
        const ts=now();
        const duration=(ts-startTs)/1000;
        const activeTime=((lastActiveStart?ts-lastActiveStart:0)+ (lastActiveStart?0:0));
        const active_sec=Math.max(0,(duration - hiddenTotal/1000));
        const avgMouseSpeed=mouse.moveCount?mouse.sumSpeed/mouse.moveCount:0;
        const mouseVar=mouse.moveCount?Math.max(0,(mouse.sumSpeedSq/mouse.moveCount)-avgMouseSpeed*avgMouseSpeed):0;
        const avgClickDelay=clicks.interDelays.length?clicks.interDelays.reduce((a,b)=>a+b,0)/clicks.interDelays.length:0;
        const avgDwell=keys.dwellCount?keys.sumDwell/keys.dwellCount:0;
        const avgScrollSpeed=scrolls.count?scrolls.sumSpeed/scrolls.count:0;
        return {
            duration:parseFloat(duration.toFixed(3)),
            active_ratio:parseFloat((active_sec?active_sec/duration:0).toFixed(3)),
            first_interaction_delay:firstInteractionDelay===null?null:parseFloat(firstInteractionDelay.toFixed(3)),
            focus_count:focusCount,
            hidden_seconds:parseFloat((hiddenTotal/1000).toFixed(3)),
            mouse_move_count:mouse.moveCount,
            mouse_total_distance:parseFloat(mouse.totalDist.toFixed(3)),
            mouse_avg_speed:parseFloat(avgMouseSpeed.toFixed(6)),
            mouse_speed_variance:parseFloat(mouseVar.toFixed(6)),
            click_count:clicks.count,
            avg_click_delay:parseFloat(avgClickDelay.toFixed(3)),
            scroll_events:scrolls.count,
            max_scroll_depth:scrolls.maxDepth,
            scroll_avg_speed:parseFloat(avgScrollSpeed.toFixed(6)),
            key_events:keys.count,
            key_avg_dwell:parseFloat(avgDwell.toFixed(3)),
        };
    }

    async function sendEvent(name,data,useBeacon=false){
        const payload=JSON.stringify({event:name,session:SESSION_ID,data});
        const encrypted=await encrypt(payload);
        if(useBeacon && navigator.sendBeacon){
            const blob=new Blob([encrypted],{type:"text/plain"});
            navigator.sendBeacon(ENDPOINT,blob);
            return;
        }
        try{ await fetch(ENDPOINT,{method:"POST",headers:{"Content-Type":"text/plain"},body:encrypted,keepalive:true}); }catch(e){}
    }

    await sendEvent("session_start",assembleFeatures());
    const intervalId=setInterval(()=>{ sendEvent("heartbeat",assembleFeatures()); },BATCH_INTERVAL);

    setTimeout(()=>{ clearInterval(intervalId); sendEvent("session_end",assembleFeatures(),true); }, 30000);
    window.addEventListener("pagehide",()=>{ clearInterval(intervalId); sendEvent("session_end",assembleFeatures(),true); });
    window.addEventListener("beforeunload",()=>{ clearInterval(intervalId); });
})();