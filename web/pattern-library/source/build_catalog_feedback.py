#!/usr/bin/env python3
"""Extract traceable garment adjustment signals from the published review CSV."""
import argparse
import csv
from collections import Counter
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

DATASET_URL = "https://www.kaggle.com/datasets/nicapotato/womens-ecommerce-clothing-reviews"
DATASET_NAME = "Women's E-Commerce Clothing Reviews"
DATASET_FILE = "Womens Clothing E-Commerce Reviews.csv"
FIT_URL = "https://www.kaggle.com/datasets/rmisra/clothing-fit-dataset-for-size-recommendation"
FIT_CITATION = "https://cseweb.ucsd.edu/~jmcauley/pdfs/recsys18e.pdf"
# These are candidate pattern actions. No source review supplies a calibrated target for a different garment.
PARTS = {
    "sleeve_length": ("袖长", r"sleeves?|arm length", "肩点至袖口或腋下至袖口", "袖山、袖口周长"),
    "upper_arm": ("上臂松量", r"upper arms?|biceps?|sleeves?", "上臂围和袖底松量", "袖长、袖山"),
    "cuff": ("袖口", r"cuffs?|wrist(?:s| opening)?", "袖口展开宽和穿脱所需开口", "袖长、扣位"),
    "armhole": ("袖窿", r"arm\s?holes?|underarms?|arm openings?", "袖窿深、周长和抬手量", "肩线、袖山缝长和剪口"),
    "shoulder": ("肩宽与肩点", r"shoulders?|shoulder seams?", "单肩长、肩点和背肩宽", "领宽和袖山对位"),
    "neckline": ("领口", r"neck\s?lines?|neck opening|neck\b(?!\s+(?:and|shoulder))|v.neck|collars?", "前后领深、领宽和领口周长", "肩线、领口贴边"),
    "chest": ("胸围与胸省", r"bust(?:line)?|chest|boobs|breasts?|breast area", "胸围、胸高和胸腰差", "肩线、腰线和门襟"),
    "waist_fit": ("腰围与腰头", r"waist(?:band)?|midsection|tumm?y|stomach|waist band", "平量腰宽、腰围和腰头弹伸量", "裆深或胸腰高度"),
    "waist_height": ("腰线高度", r"waist(?:band|line)?|waist band", "肩腰长或腰头至裆点高度", "腰围和原有松量"),
    "hip": ("臀围与后片", r"hips?|seat|butt|bottom area|backside|rear", "成衣臀围、后裆松量", "腰头、侧缝对位"),
    "thigh": ("大腿松量", r"thighs?|upper legs?", "大腿围和胯下松量", "臀围、膝位"),
    "leg_opening": ("裤腿与脚口", r"leg openings?|ankles?|calves|calf|pant legs?|trouser legs?", "膝围、脚口宽和步幅", "裤长、膝位"),
    "inseam": ("裤长与内长", r"inseams?|pant legs?|trouser legs?|pants|jeans|trousers|leggings", "内侧缝长、外长和目标裤口高度", "膝位、裆线和脚口"),
    "rise": ("前后裆深", r"(?:front |back )?rise|crotch(?: area)?", "前后裆长、实际腰高和坐下余量", "腰围和臀围"),
    "hem_length": ("衣长与下摆高度", r"body length|front length|back length|hem(?:line)?|length|(?:dress|skirt|top|blouse|shirt|sweater|jacket|coat|cardigan)s?", "肩至下摆或腰至裙摆长", "腰线和下摆工艺"),
    "torso": ("躯干长度", r"torso|bodice", "肩腰长，连体装需量肩裆环长", "肩线、胸高和腰围"),
    "hem_width": ("摆量", r"hem(?:line)?|skirt bottom|lower hem", "下摆周长和开衩活动量", "腰臀围与摆口曲线连续性"),
    "straps": ("肩带", r"straps?|spaghetti straps?", "肩带总长、调节范围和肩位", "胸高、前后连接点"),
    "pockets": ("口袋", r"pockets?|pocket bags?", "袋口宽深、袋布净深和手部取物量", "侧缝、门襟和体积"),
    "closure": ("开合与门襟", r"zippers?|zips?|buttons?|snaps?|closures?|plackets?", "开口有效长、扣位间距和门襟重叠量", "中线、缝合与穿脱量"),
    "lining": ("里布与透视", r"linings?|liners?|underlayers?|slips?", "里布覆盖、下摆落差及成衣松量", "主体轮廓和材料伸长差"),
    "size": ("尺码级差", r"", "该尺码的人体表、成衣关键围度和相邻尺码级差", "已通过的平衡和缝合接口"),
    "variant": ("变体", r"", "目标人群人体表和跨尺寸控制点", "原版尺码、风格与放码谱系"),
    "material": ("面料与弹性", r"", "经纬伸长、回复、缩水和手感要求", "原版结构及放松量"),
}
ACTIONS = {
    "lengthen": "加长", "shorten": "缩短", "widen": "放宽或增加松量", "narrow": "收窄或减少松量",
    "raise": "提高", "lower": "降低", "add": "增加或补足", "rework": "调整结构",
    "grade": "核对尺码并校正级差", "petite": "增加娇小版", "tall": "增加高个版",
    "plus": "增加大码版", "curvy": "增加曲线身型版", "color": "增加颜色选项",
    "alternate": "增加版型选项", "fabric": "调整面料或里布选项",
}
LONG = r"(?:(?:too|overly|a bit|a little|slightly|very|quite|really|rather) long|longer than (?:expected|pictured|described)|way long)"
SHORT = r"(?:(?:too|overly|a bit|a little|slightly|very|quite|really|rather) short|shorter than (?:expected|pictured|described)|way short)"
TIGHT = r"(?:(?:too|overly|a bit|a little|slightly|very|quite|really|rather) (?:tight|narrow|small|snug)|tighter than (?:expected|pictured)|constrict(?:ing|ive)|restricted)"
LOOSE = r"(?:(?:too|overly|a bit|a little|slightly|very|quite|really|rather) (?:loose|wide|large|big|baggy)|looser than expected|gaping|gapes)"
HIGH = r"(?:too high|higher than expected|a bit high)"
LOW = r"(?:too low|lower than expected|a bit low)"
LENGTHS = ("sleeve_length", "inseam", "torso", "straps", "hem_length")
FIT = ("cuff", "armhole", "shoulder", "upper_arm", "chest", "waist_fit", "hip", "thigh", "leg_opening", "hem_width")
JOIN = r"(?:\s+(?:it|was|are|were|is|felt|feels|fit|fits|looked|looks|being|seems?|seemed|ended up|got|gotten|has been|just|only|still|also|a|the|little|much|way|far|almost|even|somewhat|run|runs|ran|fit me|on me))*\s+"
DIRECTIONAL = []
for key, qualifiers in (
    *((part, ((LONG, "shorten"), (SHORT, "lengthen"))) for part in LENGTHS),
    *((part, ((TIGHT, "widen"), (LOOSE, "narrow"))) for part in FIT),
    ("waist_height", ((HIGH, "lower"), (LOW, "raise"))),
    ("rise", ((HIGH, "lower"), (LOW, "raise"), (LONG, "shorten"), (SHORT, "lengthen"), (TIGHT, "widen"))),
    ("neckline", ((HIGH, "lower"), (LOW, "raise"), (LOOSE, "narrow"), (TIGHT, "widen"))),
):
    for qualifier, action in qualifiers:
        root = PARTS[key][1]
        a = rf"\b(?:{root})\b{JOIN}(?:{qualifier})\b"
        b = rf"\b(?:{qualifier})\b(?:\s+(?:for me|on me|right|especially|particularly))?\s+(?:around|over|through|above|in|across|at|on|at the)\s+(?:(?:my|the|your)\s+)?(?:{root})\b"
        DIRECTIONAL.append((key, action, re.compile(rf"(?:{a}|{b})", re.I)))

EXPLICIT = [
    ("inseam", "shorten", r"(?:had|have|need|needed|going|want|wanted) to (?:get (?:these|them|the pants|the jeans) hemmed|hem (?:these|them|the (?:pants|jeans|trousers)))"),
    ("hem_length", "shorten", r"(?:had|have|need|needed|want|wanted) to (?:hem|shorten) (?:the|this|my) (?:dress|skirt|top|blouse|shirt|coat|hem)"),
    ("sleeve_length", "shorten", r"(?:had|have|need|needed|want|wanted) to shorten (?:the |my )?sleeves"),
    ("sleeve_length", "lengthen", r"(?:wish|wished) (?:the |these |my )?sleeves were (?:a (?:little|bit) )?longer"),
    ("sleeve_length", "shorten", r"(?:wish|wished) (?:the |these |my )?sleeves were (?:a (?:little|bit) )?shorter"),
    ("hem_length", "lengthen", r"(?:wish|wished) (?:it|this|the (?:shirt|dress|skirt|top)|the length) (?:was|were) (?:a (?:little|bit) )?longer"),
    ("hem_length", "shorten", r"(?:wish|wished) (?:it|this|the (?:shirt|dress|skirt|top)|the length) (?:was|were) (?:a (?:little|bit) )?shorter"),
    ("chest", "widen", r"(?:gaps?|gaping|gaped|pull(?:s|ed|ing))\s+(?:open\s+)?(?:around|at|over|in|across)\s+(?:the |my )?(?:bust|chest|boobs)"),
    ("waist_fit", "narrow", r"(?:gaps?|gaping|gaped)\s+(?:around|at|in)\s+(?:the |my )?(?:waist|waistband)"),
    ("closure", "rework", r"(?:zippers?|zip)\s+(?:gets? stuck|broke|breaks|split|snags?|is difficult|wouldn.t (?:close|work|zip)|won.t (?:close|work|zip)|kept (?:catching|sticking))"),
    ("closure", "rework", r"(?:buttons? (?:fell|came) off|button holes? (?:were|are) too small|(?:fabric|lining|tulle) (?:keeps? )?(?:catch(?:es|ing)|gets? caught) in the zipper)"),
    ("pockets", "add", r"(?:wish(?:ed)?|would (?:be nice|love|prefer|be better))\s+(?:it|they|this|these)?\s*(?:had|have|with|to have|there (?:were|was))\s+(?:real |more |side |back |deeper )?pockets?"),
    ("pockets", "add", r"(?:no |lacks? |without )(?:usable |side |back |functional |real )?pockets?\b"),
    ("pockets", "widen", r"pockets? (?:are|were|is) (?:a bit |way )?too (?:small|shallow|narrow)|pockets? (?:barely|can.t|cannot|won.t|does not|don.t) fit"),
    ("pockets", "rework", r"pockets? (?:flare|stick|bulge|puff) out"),
    ("lining", "add", r"(?:wish(?:ed)?|would (?:love|prefer))\s+(?:it|they|this|these)?\s*(?:had|have|with|to have|there (?:were|was))\s+(?:a )?(?:full |thicker |longer )?(?:lining|liner|slip)"),
    ("lining", "add", r"(?:(?:too|very|completely|totally) sheer|(?:see.through|transparent) (?:in|at|around|even with)|completely see.through)"),
    ("lining", "lengthen", r"(?:linings?|liners?|underlayers?|slips?) (?:is|was|are|were) (?:much |way )?too short"),
    ("material", "fabric", r"(?:fabric|material) (?:was|is|feels?|seems?) (?:way |much )?too (?:thin|thick|stiff|scratchy|heavy|itchy)"),
    ("material", "fabric", r"(?:no|very little|not enough|needs more|wish.*?had(?: a (?:bit|little) more)?) (?:stretch|give|elasticity)"),
    ("material", "fabric", r"(?:shrank|shrunk|shrinks) (?:in (?:the )?(?:wash|dryer)|after (?:the first )?wash(?:ing)?|a (?:lot|ton)|when (?:i|you) wash)"),
    ("size", "grade", r"\b(?:runs?|ran|sizing (?:is|was)) (?:way |very |really |extremely |a bit |a little |slightly |somewhat )?(?:small|large|big)\b"),
    ("size", "grade", r"\b(?:inconsistent sizing|size chart (?:is|was) (?:wrong|off|inaccurate)|doesn.t match the size chart)\b"),
    ("variant", "petite", r"(?:wish(?:ed)?|would (?:love|prefer)|want|need)\b.{0,46}\b(?:a petite|in petites?|petite sizes?|petite version)\b|(?:doesn.t|does not|didn.t|did not|not) come in petite\b"),
    ("variant", "tall", r"(?:wish(?:ed)?|would (?:love|prefer)|want|need)\b.{0,46}\b(?:a tall|in tall|tall sizes?|tall version)\b|(?:doesn.t|does not|not) come in tall\b"),
    ("variant", "plus", r"(?:wish(?:ed)?|would (?:love|prefer)|want|need)\b.{0,46}\b(?:in plus|plus sizes?|larger sizes?|more sizes)\b"),
    ("variant", "curvy", r"(?:wish(?:ed)?|would (?:love|prefer)|want|need)\b.{0,46}\b(?:a curvy|in curvy|curvy fit|curvy version)\b"),
    ("variant", "color", r"(?:wish(?:ed)?|would (?:love|prefer)|want)\b.{0,48}\b(?:more colou?rs?|(?:had it|came|offered) in (?:black|a different|another|navy|white|blue|red|green))\b"),
    ("variant", "alternate", r"(?:wish(?:ed)?|would (?:love|prefer))\b.{0,48}\b(?:sleeveless version|longer version|shorter version|version with sleeves|more (?:length|sleeve) options|long sleeve version)\b"),
]
EXPLICIT = [(part, action, re.compile(p, re.I)) for part, action, p in EXPLICIT]
CLAUSES = re.compile(r"(?<=[.!?;])\s+|[\r\n]+|\s+\b(?:but|however|although|except)\b\s+", re.I)
NEGATION = re.compile(r"\b(?:not|isn.t|wasn.t|weren.t|aren.t|neither|never|without)\b(?:\s+\w+){0,4}\s*$", re.I)
DIRECTION_CUE = re.compile(r"\b(?:long|short|tight|narrow|small|snug|loose|wide|large|big|baggy|high|low|longer|shorter|gapes|gaping|tighter|looser|higher|lower|constricting|restrict(?:ed|ive))\b", re.I)
EXPLICIT_CUE = re.compile(r"\b(?:pockets?|zippers?|zips?|linings?|slips?|buttons?|seams?|wish(?:ed)?|would|wants?|need(?:ed|s)?|runs?|ran|sizing|hem(?:med)?|stretch|give|elasticity|shr[ua]nk|shrinks|sheer|transparent|see.through|gaps?|gaping|gaped|pull(?:s|ed|ing)|material|fabric)\b", re.I)
BODY_DESCRIPTION = re.compile(r"\b(?:i am|i.m|my body is)\s*$", re.I)
CONDITIONAL = re.compile(r"\b(?:would (?:be|have been)|worry about|worried about|fear(?:ed|ing)?)\b(?:\s+\w+){0,7}\s*$", re.I)
PART_MARKERS = {key: re.compile(rf"\b(?:{pattern})\b", re.I) for key, (_, pattern, _, _) in PARTS.items() if pattern}
DUPLICATE = re.compile(r"\W+")
CLASS_LABELS = dict(zip(
    ("Dresses","Knits","Blouses","Sweaters","Pants","Jeans","Fine gauge","Skirts","Jackets","Lounge","Swim","Outerwear","Shorts","Sleep","Legwear","Intimates","Layering","Trend","Casual bottoms","Chemises"),
    ("连衣裙","针织上衣","衬衫","毛衣","长裤","牛仔裤","细针织","半身裙","夹克","居家服","泳装","外套","短裤","睡衣","贴腿服装","内衣","打底服","时装","休闲下装","衬裙")
))
CLASS_LABELS.update({"dress":"连衣裙", "dresses":"连衣裙", "gown":"礼服", "sheath":"直筒连衣裙", "shift":"宽松直身裙", "jumpsuit":"连体长裤", "romper":"连体短裤", "top":"上衣", "tops":"上衣", "sweater":"毛衣", "jacket":"夹克", "coat":"外套", "outerwear":"外套", "blouse":"衬衫", "skirt":"半身裙", "pants":"长裤", "jeans":"牛仔裤", "shorts":"短裤", "leggings":"打底裤", "bottoms":"下装", "new":"未细分", "sale":"未细分"})
PANTS = {"Pants", "Jeans", "Shorts", "Legwear", "Casual bottoms"}


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def signals(text, class_name):
    seen = set()
    for clause in CLAUSES.split(text):
        clause = normalize(clause)
        results = []
        added = [item for item in EXPLICIT] if EXPLICIT_CUE.search(clause) else []
        if DIRECTION_CUE.search(clause):
            present = {part for part, pattern in PART_MARKERS.items() if pattern.search(clause)}
            added.extend(item for item in DIRECTIONAL if item[0] in present)
        for part, action, pattern in added:
            if part == "inseam" and class_name not in PANTS and "pants" not in clause.lower() and "jeans" not in clause.lower():
                continue
            for match in pattern.finditer(clause):
                before = clause[:match.start()]
                if NEGATION.search(before) or CONDITIONAL.search(before) or BODY_DESCRIPTION.search(before):
                    continue
                if (part, action) in seen:
                    continue
                if part in ("size", "hem_length") and (part, action, match.span()) in results:
                    continue
                results.append((part, action, match.span()))
        specific = [span for part, _, span in results if part in LENGTHS and part != "hem_length"]
        for part, action, (start, end) in results:
            if part == "hem_length" and any(start <= right and left <= end for left, right in specific):
                continue
            if (part, action) in seen:
                continue
            seen.add((part, action))
            left, right = (0, len(clause)) if len(clause) <= 240 else (max(0, start-35), min(len(clause), end+62))
            yield part, action, clause[left:right].strip()


def extract(input_rows, code, text_key, index_key, id_key, garment_key, rating_key):
    groups, rows, review_keys = Counter(), [], set()
    counts = Counter()
    for offset, source in enumerate(input_rows):
        counts["input_rows"] += 1
        text = (source.get(text_key) or "").strip()
        if not text:
            continue
        counts["text_rows"] += 1
        class_name = source.get(garment_key, "")
        duplicate_key = (source[id_key], DUPLICATE.sub(" ", text.casefold()).strip())
        if duplicate_key in review_keys:
            counts["repeated_text_same_product"] += 1
            continue
        review_keys.add(duplicate_key)
        detections = list(signals(text, class_name))
        if not detections:
            continue
        counts["matched_reviews"] += 1
        index = int(source[index_key]) if index_key is not None else offset
        for part, action, snippet in detections:
            counts["issue_rows"] += 1
            groups[part] += 1
            rows.append({
                "id": f"{code}-{index:06d}-{part}-{action}",
                "review_id": f"{code}-{index:06d}",
                "source_id": code,
                "source_index": index,
                "product_id": str(source[id_key]),
                "garment": CLASS_LABELS.get(class_name, class_name or "未分类"),
                "source_garment": class_name,
                "part": part,
                "action": action,
                "evidence": snippet,
                "rating": source.get(rating_key, ""),
            })
    return counts, groups, rows


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", type=Path, required=True)
    cli.add_argument("--fit-source", type=Path)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    with ZipFile(args.source) as archive, archive.open(DATASET_FILE) as stream:
        counts, groups, rows = extract(csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig")),
                                      "WEC", "Review Text", "", "Clothing ID", "Class Name", "Rating")
    args.output.mkdir(parents=True, exist_ok=True)
    sources = {"WEC": {"title": DATASET_NAME, "url": DATASET_URL, "license": "CC0-1.0",
                       "filename": DATASET_FILE, "archive_sha256": sha256(args.source.read_bytes()).hexdigest(), "counts": dict(counts)}}
    if args.fit_source:
        fit_hash = sha256(args.fit_source.read_bytes()).hexdigest()
        with ZipFile(args.fit_source) as archive:
            for code, title, filename, rating in (
                ("RTR", "Rent the Runway", "renttherunway_final_data.json", "rating"),
                ("MOD", "ModCloth", "modcloth_final_data.json", "quality"),
            ):
                with archive.open(filename) as stream:
                    other_counts, other_groups, other_rows = extract((json.loads(line) for line in stream),
                        code, "review_text", None, "item_id", "category", rating)
                sources[code] = {"title": title + " · Clothing Fit Dataset", "url": FIT_URL,
                    "license": "CC-BY-4.0", "filename": filename, "citation": FIT_CITATION,
                    "archive_sha256": fit_hash, "counts": dict(other_counts)}
                counts.update(other_counts)
                groups.update(other_groups)
                rows.extend(other_rows)
    parts = {k: {"label": label, "measurement": measurement, "preserve": preserve}
             for k, (label, _, measurement, preserve) in PARTS.items()}
    out = {"schema": "pattern-agent-feedback/1", "sources": sources, "counts": dict(counts),
           "issue_counts": dict(groups), "parts": parts, "actions": ACTIONS, "entries": rows}
    (args.output / "review-signals.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    fields = (*rows[0], "part_zh", "candidate_zh", "measurement_zh", "preserve_zh", "source_url", "review_state")
    with (args.output / "review-signals.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            part, action = row["part"], row["action"]
            evidence = row["evidence"]
            if evidence.startswith(("=", "+", "-", "@")):
                evidence = "'" + evidence
            writer.writerow(dict(row, evidence=evidence, part_zh=parts[part]["label"], candidate_zh=ACTIONS[action], measurement_zh=parts[part]["measurement"],
                                 preserve_zh=parts[part]["preserve"], source_url=sources[row["source_id"]]["url"], review_state="needs_confirmation"))
    print(json.dumps({"counts": dict(counts), "issue_counts": dict(groups), "sources": {k: x["counts"] for k, x in sources.items()},
                      "unique_products": len({(r["source_id"], r["product_id"]) for r in rows})}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
