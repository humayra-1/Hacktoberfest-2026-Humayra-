import html
import io
import os
import time

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

API_KEY = os.getenv("GEMINI_API_KEY", "")   # optional; you can also paste the key in the sidebar

PREFERRED = ["gemma-4-26b-a4b-it", "gemma-4-31b-it"]   # open-weight Gemma 4 models
BACKUP = "gemini-3.8-flash"                             # ONLY used if you tick the sidebar checkbox

GUIDE = """You are "Can I Eat This?", a warm, funny, genuinely knowledgeable food companion for students in Bangladesh.
You think like a good home cook who also understands food safety. Reply in: <<LANG>>. Vibe: <<TONE>>.

CORE RULE: TASTE and SAFETY are two different questions. Never mix them up.
- Taste = would these flavors and textures work together? A weird pairing is NOT automatically unsafe.
- Safety = could this make someone sick? A tasty pairing is NOT automatically safe (e.g. raw chicken).
Only raise a safety concern when there is a real, specific reason (raw or undercooked meat/eggs, cross-contamination,
spoilage, mold, unpasteurized items, leftover rice kept warm too long, common allergens like peanuts/dairy/gluten).
If a combo is safe, say so plainly and don't invent risks. If safety depends on how it's prepared, say exactly what it depends on.

When the user names foods (typed text is enough, a photo is optional) or shows them in a photo, give a full answer in markdown:
**<verdict emoji> <funny bold title>**  (🟢 great, 🟡 weird but works, 🔴 not a good match; this emoji is about TASTE only)
**👅 Taste check:** 3-5 sentences of real reasoning. Say what each food contributes (sweetness, salt, acidity, fat, crunch, creaminess)
and why they balance or clash. Be specific to these foods, never generic.
**🍳 How I'd make it:** a concrete, easy way to prepare it (amounts or steps, 2-4 sentences). Use ingredients easy to find in Bangladesh.
**🛡️ Food safety check:** completely separate from taste. Start with ✅ No real concerns, ⚠️ Be careful, or ⛔ Not safe, then explain why
in 1-3 sentences, with any useful handling tip.
**📊 Taste score: X/10:** one sentence explaining the score. It is about flavor only.
Aim for 150-250 words.

If the user asks a follow-up (make it healthier, add chili, what about X instead...), answer naturally and directly, building on the
combo we already discussed. Do NOT repeat the template or re-score unless they ask for a new verdict. Keep follow-ups to 40-150 words.
If a photo contains no food, say so kindly. If a detail matters for safety (like how something was cooked), mention it instead of guessing.
Never give medical advice; if allergies or health conditions come up, suggest asking a doctor."""

ACK = "Got it! I'll keep taste and food safety completely separate, reason about the specific foods, and build on earlier messages."
GREETING = ("Hey! 👋 I'm your food-combo buddy. Tell me what you're mixing (like *banana + muri*), "
            "or attach a photo with the ➕ button. I'll tell you how it tastes, how I'd make it, "
            "and whether it's actually safe, as two separate things. 😋")
SURPRISE = "Surprise me with one weird but genuinely tasty, safe combo (easy to find in Bangladesh) and give me the full breakdown!"
PRESETS = ["muri + banana", "fuchka + ice cream", "rice + Nutella",
           "Pran mango juice + biscuits", "raw chicken + salad", "milk + lemon"]
CHIPS = [("🥗 Make it healthier", "How can I make this combo healthier?"),
         ("🌶️ Make it spicier", "How do I make this combo spicier?"),
         ("🇧🇩 Street-food version", "Give me a Bangladeshi street-food version of this combo")]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap');
:root { --navy:#14213d; }
html, body, .stApp, button, input, textarea { font-family:'Fredoka','Comic Sans MS',sans-serif !important; }
.stApp { background-color:#fff3c4; background-image:radial-gradient(#ffd966 2px,transparent 2px); background-size:28px 28px; }
header[data-testid="stHeader"] { background:transparent; }
section[data-testid="stSidebar"] { background:#ffe8a3; border-right:4px solid var(--navy); }
.title-box { text-align:center; margin-bottom:6px; }
.title-box h1 { font-size:2.3rem; margin:0; color:var(--navy); text-shadow:3px 3px 0 #ff9f1c; }
.mascot { font-size:3.4rem; display:inline-block; animation:bounce 1.2s infinite; }
@keyframes bounce { 0%,100%{transform:translateY(0) rotate(-6deg)} 50%{transform:translateY(-12px) rotate(6deg)} }
.stApp p, .stApp li, .stApp strong, .stApp em, .stApp label, .stApp .stMarkdown, [data-testid="stWidgetLabel"] p, .stApp h3, .stSpinner * { color:var(--navy) !important; }
header[data-testid="stHeader"] *, header[data-testid="stHeader"] svg { color:var(--navy) !important; fill:var(--navy) !important; }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {
  background:#fff !important; border:3px solid var(--navy) !important; border-radius:50% !important; box-shadow:3px 3px 0 var(--navy); transition:transform .15s; }
[data-testid="stExpandSidebarButton"] *, [data-testid="stSidebarCollapseButton"] *, [data-testid="collapsedControl"] * { color:var(--navy) !important; fill:var(--navy) !important; }
[data-testid="stExpandSidebarButton"]:hover, [data-testid="stSidebarCollapseButton"]:hover { transform:scale(1.15) rotate(8deg); }
[data-testid="stBottom"], [data-testid="stBottom"] > div { background:#fff3c4 !important; }
div[data-testid="stChatInput"], div[data-testid="stChatInput"] > div { background:#fff !important; }
div[data-testid="stChatInput"] { border:3px solid var(--navy); border-radius:22px; box-shadow:4px 4px 0 var(--navy); transition:all .15s; }
div[data-testid="stChatInput"]:focus-within { box-shadow:5px 5px 0 #ff6b9d; transform:translateY(-2px); }
div[data-testid="stChatInput"] textarea { color:var(--navy) !important; background:#fff !important; }
div[data-testid="stChatInput"] textarea::placeholder { color:#14213d99 !important; }
/* attach (+) and send buttons: WHITE icon on a navy circle so they are always visible */
div[data-testid="stChatInput"] button { background:var(--navy) !important; border-radius:50% !important; border:none !important; transition:transform .15s; }
div[data-testid="stChatInput"] button:hover { transform:scale(1.12) rotate(8deg); background:#ff6b9d !important; }
div[data-testid="stChatInput"] button, div[data-testid="stChatInput"] button * { color:#fff !important; fill:#fff !important; }
div[data-baseweb="select"] > div { background:#fff !important; border:3px solid var(--navy) !important; border-radius:14px !important; }
div[data-baseweb="select"] * { color:var(--navy) !important; }
.stButton > button { border:3px solid var(--navy) !important; border-radius:18px; font-weight:700; background:#fff; color:var(--navy) !important; box-shadow:4px 4px 0 var(--navy); transition:all .1s; }
.stButton > button:hover { background:#ffe066 !important; transform:translate(-2px,-2px) rotate(-1deg); box-shadow:6px 6px 0 var(--navy); }
.stButton > button:active { transform:translate(3px,3px); box-shadow:1px 1px 0 var(--navy); }
div[data-testid="stChatMessage"] { background:#fffdf5; border:3px solid var(--navy); border-radius:20px; box-shadow:4px 4px 0 var(--navy); margin-bottom:14px; transition:transform .15s; }
div[data-testid="stChatMessage"]:hover { transform:translateY(-2px); }
.tag { font-size:.75rem; color:#5a4a1f !important; font-weight:600; margin-top:6px; }
.cook { font-weight:700; font-size:1.1rem; color:var(--navy); }
.cook span { display:inline-block; font-size:1.8rem; animation:bounce .7s infinite; }
.cook span:nth-child(2) { animation-delay:.15s } .cook span:nth-child(3) { animation-delay:.3s }
</style>
"""
COOK = '<div class="cook"><span>🍳</span><span>🥘</span><span>🍜</span> Thinking about your food...</div>'


# ---------- helpers ----------
def esc(x):
    return html.escape(str(x))


@st.cache_resource(show_spinner=False)
def get_client(key):
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=45000))


@st.cache_resource(show_spinner=False)
def get_cache():
    return {}


def prep(f):
    im = Image.open(f).convert("RGB")
    im.thumbnail((768, 768))
    return im


def to_part(im):
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def build_contents(text, img, lang, tone, hist=None):
    hist = st.session_state.history if hist is None else hist
    guide = GUIDE.replace("<<LANG>>", lang).replace("<<TONE>>", tone)
    contents = [types.Content(role="user", parts=[types.Part(text=guide)]),
                types.Content(role="model", parts=[types.Part(text=ACK)])]
    for m in hist[-10:]:
        if m.get("err"):
            continue
        t = (m["text"] or "") + (" [photo attached]" if m.get("img") else "")
        contents.append(types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=t)]))
    parts = [types.Part(text=text or "(photo only, please identify the foods and judge them)")]
    if img is not None:
        parts.append(to_part(img))
    contents.append(types.Content(role="user", parts=parts))
    return contents


def raw_text(r):
    if r.text:
        return r.text
    out = []
    for c in (r.candidates or []):
        for p in ((c.content.parts if c.content else None) or []):
            if getattr(p, "text", None):
                out.append(p.text)
    return "".join(out)


def why(s):
    low = s.lower()
    if "404" in s or "not_found" in low or "no longer available" in low:
        return "isn't available to your API key"
    if "429" in s or "quota" in low or "resource_exhausted" in low:
        return "rate limit reached"
    if "timed out" in low or "timeout" in low:
        return "took too long (timeout)"
    if any(k in s for k in ("500", "503", "INTERNAL", "UNAVAILABLE")):
        return "Google server error (usually temporary)"
    return s[:110]


def stream_model(key, contents, models, backup, meta):
    """Yields text as the model writes. Reports clearly which model failed and why."""
    client = get_client(key)
    cfg = types.GenerateContentConfig(max_output_tokens=2048, temperature=0.9)
    problems = []
    for name in list(models) + ([BACKUP] if backup else []):
        for attempt in range(2):
            got = False
            try:
                for ch in client.models.generate_content_stream(model=name, contents=contents, config=cfg):
                    if ch.text:
                        got = True
                        meta["model"] = name
                        yield ch.text
                if got:
                    return
                r = client.models.generate_content(model=name, contents=contents, config=cfg)
                t = raw_text(r)
                if t:
                    meta["model"] = name
                    yield t
                    return
                problems.append(f"• `{name}` returned an empty answer")
                break
            except Exception as e:
                if got:
                    return
                s = str(e)
                if any(k in s for k in ("API key", "401", "403", "PERMISSION")):
                    raise RuntimeError("🔑 Your API key was rejected. Re-copy the whole key into the sidebar.")
                if "429" in s:
                    raise RuntimeError("⏳ Rate limit reached. Wait a few seconds and try again.")
                if "404" in s or "NOT_FOUND" in s:
                    problems.append(f"• `{name}` {why(s)}")
                    break
                if attempt == 1:
                    problems.append(f"• `{name}` {why(s)}")
                time.sleep(0.4)
    raise RuntimeError("😵 I couldn't get an answer from Gemma:\n\n" + "\n".join(problems[-4:]) +
                       "\n\nUse **🩺 Check Gemma connection** in the sidebar to see which models your key can use.")


def discover_models(key):
    found = []
    for m in get_client(key).models.list():
        n = (m.name or "").replace("models/", "")
        acts = getattr(m, "supported_actions", None) or []
        if n.startswith("gemma") and (not acts or "generateContent" in acts):
            found.append(n)
    return found


def tag_html(model, secs=None, cached=False):
    if not model:
        return ""
    label = f"{model} (open-weight)" if model.startswith("gemma") else f"{model} (backup)"
    extra = (f" • ⏱ {secs:.1f}s" if secs else "") + (" • ⚡ instant" if cached else "")
    return f'<div class="tag">🧠 {esc(label)}{extra}</div>'


def render_message(m):
    if m["role"] == "user":
        with st.chat_message("user", avatar="😋"):
            if m.get("img"):
                st.image(m["img"], width=220)
            if m.get("text"):
                st.write(m["text"])
    else:
        with st.chat_message("assistant", avatar="🍽️"):
            st.markdown(m["text"])
            st.markdown(tag_html(m.get("model"), m.get("secs"), m.get("cached")), unsafe_allow_html=True)


def answer(text, img, key, lang, tone, models, backup):
    cache = get_cache()
    ckey = (text.strip().lower(), lang, tone)
    first_turn = not st.session_state.history
    ph = st.empty()
    if img is None and first_turn and ckey in cache:
        t, model = cache[ckey]
        ph.markdown(t)
        st.markdown(tag_html(model, None, True), unsafe_allow_html=True)
        return t, model, None, True, False
    ph.markdown(COOK, unsafe_allow_html=True)
    meta, acc, t0 = {}, "", time.time()
    try:
        for piece in stream_model(key, build_contents(text, img, lang, tone), models, backup, meta):
            acc += piece
            ph.markdown(acc + " ▌")
    except Exception as e:
        ph.markdown(str(e))
        return str(e), None, None, False, True
    secs = time.time() - t0
    ph.markdown(acc)
    st.markdown(tag_html(meta.get("model"), secs), unsafe_allow_html=True)
    if img is None and first_turn and acc.strip():
        cache[ckey] = (acc, meta.get("model"))
    return acc, meta.get("model"), secs, False, False


# ---------- page ----------
st.set_page_config(page_title="Can I Eat This?", page_icon="🍽️")
st.markdown(CSS, unsafe_allow_html=True)
st.session_state.setdefault("history", [])
st.session_state.setdefault("models", list(PREFERRED))

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    key = st.text_input("🔑 API key", value=API_KEY, type="password").strip()
    pick = st.selectbox("🤖 Gemma model", st.session_state.models)
    if st.button("🩺 Check Gemma connection"):
        if not key:
            st.warning("Add your key first.")
        else:
            with st.spinner("Checking which Gemma models your key can use..."):
                try:
                    found = discover_models(key)
                except Exception as e:
                    found, err = [], str(e)
                    st.error(f"Couldn't list models: {why(err)}")
                if found:
                    ordered = [m for m in PREFERRED if m in found] + [m for m in found if m not in PREFERRED and "-it" in m]
                    st.session_state.models = ordered or found
                    st.success("Your key can use: " + ", ".join(f"`{m}`" for m in found[:6]))
                    t0 = time.time()
                    try:
                        r = get_client(key).models.generate_content(model=st.session_state.models[0], contents="Say hi in 3 words.")
                        st.success(f"`{st.session_state.models[0]}` replied in {time.time()-t0:.1f}s: {r.text.strip()[:40]}")
                    except Exception as e:
                        st.error(f"`{st.session_state.models[0]}` failed: {why(str(e))}")
                elif not found and key:
                    st.error("No Gemma models are visible to this key. Ask the organizers or enable the model in AI Studio.")
    lang = st.selectbox("🌐 Language", ["English", "Bangla (বাংলা)", "English + short Bangla translation"])
    tone = st.selectbox("🎭 Vibe", ["Funny and playful", "Extra dramatic food critic", "Serious and short"])
    backup = st.checkbox("🛟 Use Gemini if Gemma is down", value=False)
    models = [pick] + [m for m in st.session_state.models if m != pick]
    if st.button("🔥 Pre-warm demo presets"):
        if not key:
            st.warning("Add your key first.")
        else:
            bar, cache = st.progress(0), get_cache()
            for i, p in enumerate(PRESETS):
                ck = (p.lower(), lang, tone)
                if ck not in cache:
                    meta, acc = {}, ""
                    try:
                        for piece in stream_model(key, build_contents(p, None, lang, tone, hist=[]), models, backup, meta):
                            acc += piece
                        if acc.strip():
                            cache[ck] = (acc, meta.get("model"))
                    except Exception:
                        pass
                bar.progress((i + 1) / len(PRESETS))
            st.success("Presets are instant now ⚡")
    with st.expander("📷 Use my camera"):
        shot = st.camera_input("Say cheese", label_visibility="collapsed")
        if shot and st.button("Judge this photo 📸"):
            st.session_state.queued = ("", prep(shot))
    if st.button("🧹 New chat"):
        st.session_state.history = []
        st.rerun()

st.markdown('<div class="title-box"><span class="mascot">🍽️</span><h1>Can I Eat This?!</h1></div>', unsafe_allow_html=True)

job = st.session_state.pop("queued", None)
box = st.chat_input("Ask about a food combo, or attach a photo with ➕",
                    accept_file=True, file_type=["jpg", "jpeg", "png", "webp"])
if box:
    job = (box.text or "", prep(box.files[0]) if box.files else None)

if not st.session_state.history:
    with st.chat_message("assistant", avatar="🍽️"):
        st.markdown(GREETING)
for m in st.session_state.history:
    render_message(m)

if job and (job[0].strip() or job[1] is not None):
    text, img = job
    user_msg = {"role": "user", "text": text, "img": img}
    render_message(user_msg)
    with st.chat_message("assistant", avatar="🍽️"):
        if not key:
            st.warning("Paste your API key in the sidebar first 👈 (click the arrow at top-left if it's hidden).")
        else:
            reply, model, secs, cached, is_err = answer(text, img, key, lang, tone, models, backup)
            st.session_state.history += [user_msg, {"role": "assistant", "text": reply, "model": model,
                                                    "secs": secs, "cached": cached, "err": is_err}]
            if not is_err and "🟢" in reply[:120]:
                st.balloons()
            elif not is_err and ("🔴" in reply[:120] or "⛔" in reply):
                st.snow()
elif not st.session_state.history:
    st.write("**Try one:**")
    cols = st.columns(3)
    for i, p in enumerate(PRESETS):
        cols[i % 3].button(p, key=f"p{i}", on_click=lambda p=p: st.session_state.update(queued=(p, None)))
    st.button("🎲 Surprise me!", on_click=lambda: st.session_state.update(queued=(SURPRISE, None)))

last = st.session_state.history[-1] if st.session_state.history else None
if last and last["role"] == "assistant" and not last.get("err"):
    st.write("**Keep chatting:**")
    cc = st.columns(3)
    for i, (label, q) in enumerate(CHIPS):
        cc[i].button(label, key=f"chip{len(st.session_state.history)}_{i}",
                     on_click=lambda q=q: st.session_state.update(queued=(q, None)))