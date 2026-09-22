"""A request-rewriting proxy between scry's openai_compat provider and mlx_vlm.server, so a variant can be made
through config alone ([model] base_url points here). Two rewrites, each a flag, each logged per request:
  --temperature T   set the request's sampling temperature (the provider sends none; the server then uses the model's
                    generation_config, 1.0 for the 27B)
  --schema-in-system  append the request's own response_format JSON schema (field descriptions included) to the
                    system message, as text, the way the Anthropic API shows the model the schema's descriptions
Everything else passes through unchanged. Stdlib only."""
import argparse, json, sys, time, threading, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, required=True)
ap.add_argument("--upstream", default="http://127.0.0.1:8081")
ap.add_argument("--temperature", type=float, default=None)
ap.add_argument("--schema-in-system", action="store_true")
ap.add_argument("--log", required=True)
args = ap.parse_args()

SCHEMA_INTRO = ("\n\nThe answer is one JSON object matching this JSON schema. Each field's description says what the "
                "field means and holds; read them before answering:\n")

lock = threading.Lock()
first_system_saved = False


def rewrite(body: dict) -> dict:
    info = {"temperature_before": body.get("temperature"), "system_chars_before": None, "system_chars_after": None}
    if args.temperature is not None:
        body["temperature"] = args.temperature
    if args.schema_in_system:
        rf = body.get("response_format") or {}
        schema = (rf.get("json_schema") or {}).get("schema")
        msgs = body.get("messages") or []
        if schema is not None and msgs and msgs[0].get("role") == "system" and isinstance(msgs[0].get("content"), str):
            before = msgs[0]["content"]
            info["system_chars_before"] = len(before)
            msgs[0]["content"] = before + SCHEMA_INTRO + json.dumps(schema, indent=1)
            info["system_chars_after"] = len(msgs[0]["content"])
    info["temperature_after"] = body.get("temperature")
    return info


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # quiet
        pass

    def do_POST(self):
        global first_system_saved
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        t0 = time.monotonic()
        try:
            body = json.loads(raw)
        except ValueError:
            body = None
        info = {}
        if isinstance(body, dict):
            info = rewrite(body)
            raw = json.dumps(body).encode()
            if args.schema_in_system and not first_system_saved:
                with open(args.log + ".system.txt", "w") as f:
                    f.write(body["messages"][0]["content"])
                first_system_saved = True
        req = urllib.request.Request(args.upstream + self.path, data=raw, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Authorization": self.headers.get("Authorization", "")})
        try:
            with urllib.request.urlopen(req, timeout=3600) as resp:
                status, out = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, out = e.code, e.read()
        except Exception as e:
            status, out = 502, json.dumps({"error": f"proxy: {type(e).__name__}: {e}"}).encode()
        info.update({"path": self.path, "status": status, "wall_s": round(time.monotonic() - t0, 1),
                     "model": (body or {}).get("model"), "t": time.strftime("%H:%M:%S")})
        try:
            u = json.loads(out).get("usage") or {}
            info["prompt_tokens"], info["completion_tokens"] = u.get("prompt_tokens"), u.get("completion_tokens")
        except Exception:
            pass
        with lock, open(args.log, "a") as f:
            f.write(json.dumps(info) + "\n")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


print(f"proxy :{args.port} -> {args.upstream} temperature={args.temperature} schema_in_system={args.schema_in_system}", flush=True)
ThreadingHTTPServer(("127.0.0.1", args.port), H).serve_forever()
