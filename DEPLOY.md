# Deploy the agent service to Render

## 1. Push vc-brain to GitHub
From inside the `vc-brain/` folder:
```bash
git init
git add .
git commit -m "VC Brain agent service + prep pack"
# create an empty repo on github.com first (no README), then:
git branch -M main
git remote add origin https://github.com/<you>/vc-brain.git
git push -u origin main
```
`.gitignore` already excludes `.env`, so your keys never get committed. Good.

## 2. Deploy on Render
1. render.com → New → **Blueprint** (it reads `render.yaml` at the repo root).
   - Or: New → **Web Service**, connect the repo, set **Root Directory = agent-service**,
     Build = `pip install -r requirements.txt`, Start = `uvicorn main:app --host 0.0.0.0 --port $PORT`.
2. It deploys with `USE_STUBS=true` — no keys needed yet. Wait for "Live".
3. You get a URL like `https://vc-brain-agent.onrender.com`.

## 3. Verify it's up
```bash
curl https://vc-brain-agent.onrender.com/health
# -> {"ok": true, "use_stubs": true}
curl https://vc-brain-agent.onrender.com/opportunities   # returns the 3 seeded cards
```
Also open `https://vc-brain-agent.onrender.com/docs` in a browser for the Swagger UI.

## 4. Point Lovable at it
In Lovable, set the secret `AGENT_SERVICE_URL = https://vc-brain-agent.onrender.com`
(no trailing slash). The pipeline board should now render the stub opportunities.

## 5. Later — go live (when real agents are wired)
In the Render dashboard → Environment, add the real secrets:
`OPENAI_API_KEY`, `TAVILY_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
then flip `USE_STUBS=false`. Redeploy. Each `git push` to main auto-deploys.

## Demo-day note
Render free instances sleep after ~15 min idle and cold-start ~50s. Before you present,
hit `/health` once to wake it so the live demo is instant.
