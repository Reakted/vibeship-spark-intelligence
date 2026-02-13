import os, json, asyncio, httpx
from types import SimpleNamespace
import lib.advisory_synthesizer as synth
from lib.depth_trainer import DepthAnswerGenerator

def direct_probe():
    url = os.environ.get('SPARK_MINIMAX_BASE_URL', 'https://api.minimax.io/v1').rstrip('/') + '/chat/completions'
    headers = {'Authorization': f"Bearer {os.environ.get('MINIMAX_API_KEY','')}", 'Content-Type':'application/json'}
    payload = {'model': os.environ.get('SPARK_MINIMAX_MODEL','MiniMax-M2.5'), 'messages':[{'role':'user','content':'Reply with exactly: minimax-ok'}], 'max_tokens': 120, 'temperature': 0.3}
    r = httpx.post(url, headers=headers, json=payload, timeout=30)
    return {'status_code': r.status_code, 'body_preview': r.text[:220]}

def spark_probe():
    items=[SimpleNamespace(text='Use capped exponential backoff and a per-request retry budget.', confidence=0.9, source='smoke')]
    out = synth.synthesize_with_ai(items, phase='debugging', user_intent='stabilize retries', tool_name='exec_command', provider='minimax')
    st = synth.get_synth_status()
    return {'ai_timeout_s': st.get('ai_timeout_s'), 'preferred_provider': st.get('preferred_provider'), 'has_output': bool(out), 'output_preview': (out or '')[:220].replace('\n',' ')}

async def depth_probe():
    gen = DepthAnswerGenerator(provider='minimax')
    out = await gen.generate(question='How to stop retry storms?', topic='reliability', depth=1, max_depth=10, domain_id='ops', mode='classic', level_name='Build', level_lens='precise implementation', approach_guidance='Keep it short.')
    return {'provider': gen.provider, 'has_output': bool(out), 'output_preview': (out or '')[:220].replace('\n',' ')}

res = {'direct_minimax': direct_probe(), 'spark_synth_minimax': spark_probe(), 'depth_minimax': asyncio.run(depth_probe())}
print(json.dumps(res, indent=2))
