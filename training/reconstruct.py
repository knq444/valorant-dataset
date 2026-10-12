"""Standalone local reconstruction. No video downloading or private app imports."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess

from .semantic import load_semantic_dataset


def digest(path):
    value=sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): value.update(block)
    return value.hexdigest()


def reconstruct(media_map,out,ffmpeg='ffmpeg'):
    root=Path(__file__).resolve().parents[1]
    labels=root/'annotations/scenes.jsonl'
    dataset=load_semantic_dataset(labels,verify_files=False)
    mapping=json.loads(Path(media_map).read_text(encoding='utf8'))
    recipes=json.loads((root/'recipes.json').read_text())
    out=Path(out).resolve()
    if out.exists(): raise ValueError('Output must be new; no existing dataset is modified.')
    # Verify every source before creating even a partial output.
    grouped={}
    for row in dataset.records: grouped.setdefault(row['source_url'],[]).append(row)
    for source,rows in grouped.items():
        media=Path(mapping[source]).resolve()
        if not media.is_file() or digest(media)!=rows[0]['source_sha256']:
            raise ValueError('Local media must match the registered source SHA-256.')
    out.mkdir(parents=True)
    for source,rows in grouped.items():
        recipe=recipes[source];scratch=out/('_decode_'+rows[0]['source_sha256'][:16]);scratch.mkdir()
        selection=f"select=isnan(prev_selected_t)+gte(t-prev_selected_t\\,{recipe['interval_s']:.12g}),scale={recipe['width']}:-2,showinfo"
        result=subprocess.run([ffmpeg,'-hide_banner','-nostdin','-n','-i',str(Path(mapping[source]).resolve()),
          '-map','0:v:0','-an','-sn','-dn','-vf',selection,'-fps_mode','vfr','-q:v',str(recipe['jpeg_quality']),
          str(scratch/'frame_%06d.jpg')],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1800,check=False)
        if result.returncode: raise ValueError('Decoder failed; partial output preserved, no labels published.')
        if digest(Path(mapping[source]).resolve()) != rows[0]['source_sha256']:
            raise ValueError('Source changed during reconstruction; no labels published.')
        base_match=re.search(r'config in time_base:\s*(\d+)/(\d+)',result.stderr)
        if not base_match: raise ValueError('Decoder time base missing.')
        base=Fraction(int(base_match[1]),int(base_match[2]));timings=[]
        for line in result.stderr.splitlines():
            match=re.search(r'\bn:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:\s*([^\s]+)',line)
            if match:
                if int(match[1])!=len(timings): raise ValueError('Decoder index mismatch.')
                timings.append(float(match[3]) if recipe['timestamp_method']=='legacy_printed_pts' else float(int(match[2])*base))
        images=sorted(scratch.glob('frame_*.jpg'))
        if len(images)!=len(timings): raise ValueError('Decoder trace/file mismatch.')
        for row in rows:
            nearest=min(range(len(timings)),key=lambda i:abs(timings[i]-row['timestamp_s']))
            if abs(timings[nearest]-row['timestamp_s'])>1e-5 or digest(images[nearest])!=row['frame']['sha256']:
                raise ValueError('Frame pixels/time differ from inspected label. Inspect a new cohort instead.')
            target=(out/row['frame']['path']).resolve()
            if not target.is_relative_to(out): raise ValueError('Frame escapes reconstruction root.')
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(images[nearest],target)
    draft=out/'labels.jsonl.tmp';draft.write_bytes(labels.read_bytes())
    load_semantic_dataset(draft)
    draft.rename(out/'labels.jsonl')
    return {'status':'reconstructed_verified','samples':len(dataset.records),'labels_sha256':dataset.sha256}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--media-map',required=True)
    p.add_argument('--out',required=True);p.add_argument('--ffmpeg',default='ffmpeg')
    args=p.parse_args();print(json.dumps(reconstruct(args.media_map,args.out,args.ffmpeg),indent=2))

if __name__ == '__main__': main()
