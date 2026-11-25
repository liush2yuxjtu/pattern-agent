#!/usr/bin/env python3
"""Check offline HTML structure and the recorded four-pose fit review."""

from base64 import b64decode
import argparse
import binascii
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_follow_up import EMPTY, MISSING, NOT_LAST, REPEATED, has_follow_up_text, is_follow_up_heading

CATEGORIES = {'appearance', 'strain', 'stress', 'pressure', 'folds'}
SECTIONS = {'focus', 'evidence', 'follow-up', 'audit'}
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
FORBIDDEN = {'base','embed','form','iframe','link','object','script','video','audio','svg'}
CSS_REMOTE = re.compile(r'@import\b|url\s*\(', re.I)
HEADINGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
NON_REPORT_TEXT = {'head', 'style', 'script', 'template', 'nav'}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ids = {}
        self.text_ids = set()
        self.figure_ids = set()
        self.error = []
        self.links = []
        self.images = 0
        self.featured = 0
        self.folded = 0
        self.audit_folds = 0
        self.detail_count = 0
        self.figure_count = 0
        self.key_figures = set()
        self.fold_sections = set()
        self.captioned = set()
        self.summarized = set()
        self.private_keys = {}
        self.hidden_levels = set()
        self.follow_up_headings = []
        self.follow_up_text = []
        self.follow_up_closed = False
        self.follow_up_scope = None
        self.content_after_follow_up = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = attrs.get('id')
        keys = {i for _, i in self.stack if i}
        tags = {t for t, _ in self.stack}
        hidden = 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
        if key in {'focus','evidence','follow-up'} and (
            'details' in tags or hidden or self.hidden_levels
        ):
            self.error.append(f'#{key} must be visible by default')
        if key == 'follow-up':
            self.follow_up_scope = next((i for i in reversed(range(len(self.stack)))
                                         if self.stack[i][0] in {'article', 'main', 'body'}), -1)
        if 'follow-up' in keys and tag in HEADINGS and not (
            hidden or self.hidden_levels or tags & (NON_REPORT_TEXT | {'details'})
        ):
            self.follow_up_headings.append([])
        if self.follow_up_closed and self.follow_up_scope is not None and tag in {'img', 'table'}:
            if not (hidden or self.hidden_levels or tags & NON_REPORT_TEXT):
                self.content_after_follow_up = True
        if key:
            if key in self.ids:
                self.error.append(f'duplicate anchor #{key}')
            self.ids[key] = set(keys)
        if tag in FORBIDDEN or any(a.startswith('on') for a in attrs):
            self.error.append(f'unsupported active element {tag}')
        if any(a in attrs for a in ('srcset','poster','background','ping','action')):
            self.error.append(f'unsupported resource attribute on {tag}')
        if tag == 'meta' and (attrs.get('http-equiv') or '').lower() == 'refresh':
            self.error.append('unsupported automatic navigation')
        if CSS_REMOTE.search(attrs.get('style') or ''):
            self.error.append('unsupported CSS resource reference')
        if 'href' in attrs:
            href = attrs['href'] or ''
            if not href.startswith('#') or not href[1:]:
                self.error.append(f'non-local link on {tag}')
            else:
                self.links.append((href[1:], keys))
        if tag in {'details','figure'}:
            if tag=='details':
                self.detail_count += 1
                count = self.detail_count
            else:
                self.figure_count += 1
                count = self.figure_count
            key = key or f'__standalone-{tag}-{count}'
            self.private_keys[key] = tag
        if tag == 'details':
            if 'audit' in keys:
                self.audit_folds += 1
                self.fold_sections.add(key)
            if 'open' in attrs:
                self.error.append('evidence details must start closed')
        if tag == 'img':
            self.images += 1
            value = attrs.get('src','')
            match = re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)', value or '')
            try:
                if not match:
                    raise ValueError('expected embedded PNG, JPEG or WebP')
                kind, encoded = match.groups()
                raw = b64decode(encoded, validate=True)
                valid = {'png':raw.startswith(b'\x89PNG\r\n\x1a\n'),
                         'jpeg':raw.startswith(b'\xff\xd8\xff'),
                         'webp':raw.startswith(b'RIFF') and raw[8:12]==b'WEBP'}
                if not valid[kind]:
                    raise ValueError('image type does not match bytes')
            except (ValueError, binascii.Error) as e:
                self.error.append(f'image {self.images}: {e}')
            if not (attrs.get('alt') or '').strip():
                self.error.append(f'image {self.images}: missing descriptive alt')
            if 'evidence' in keys and 'details' not in tags and 'figure' in tags:
                self.featured += 1
                self.key_figures.update(k for k in keys if self.private_keys.get(k)=='figure')
            if 'audit' in keys and {'details','figure'} <= tags:
                self.folded += 1
                self.figure_ids.update(keys)
        elif 'src' in attrs:
            self.error.append(f'unsupported src on {tag}')
        if tag not in VOID:
            if hidden:
                self.hidden_levels.add(len(self.stack))
            self.stack.append((tag,key))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                if any(key == 'follow-up' for _, key in self.stack[i:]):
                    self.follow_up_closed = True
                if self.follow_up_scope is not None and self.follow_up_scope >= i:
                    self.follow_up_scope = None
                self.hidden_levels = {level for level in self.hidden_levels if level < i}
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1][0] == 'style' and CSS_REMOTE.search(data):
            self.error.append('unsupported CSS resource reference')
        elif data.strip():
            self.text_ids.update(key for _, key in self.stack if key)
            tags = {tag for tag,_ in self.stack}
            self.read_follow_up_text(data, tags)
            if 'figcaption' in tags:
                self.captioned.update(key for tag,key in self.stack if tag=='figure')
            if 'summary' in tags:
                details = [key for tag,key in self.stack if tag=='details']
                if details:
                    self.summarized.add(details[-1])

    def read_follow_up_text(self, data, tags):
        if self.hidden_levels or tags & NON_REPORT_TEXT:
            return
        if self.follow_up_closed and self.follow_up_scope is not None:
            self.content_after_follow_up = True
        if 'details' in tags or not any(key == 'follow-up' for _, key in self.stack):
            return
        if tags & HEADINGS:
            if self.follow_up_headings:
                self.follow_up_headings[-1].append(data)
        elif not tags & {'a', 'figure', 'figcaption'}:
            self.follow_up_text.append(data)

    def follow_up_errors(self):
        found = sum(is_follow_up_heading(''.join(parts)) for parts in self.follow_up_headings)
        if not found:
            return [MISSING]
        errors = [REPEATED] if found > 1 else []
        if not self.follow_up_closed or self.content_after_follow_up:
            errors.append(NOT_LAST)
        if not has_follow_up_text(' '.join(self.follow_up_text)):
            errors.append(EMPTY)
        return errors


def parse_report(path):
    page = Page()
    page.feed(path.read_text(encoding='utf-8'))
    page.close()
    return page


def verify(path, review):
    p = parse_report(path)
    problems = p.error + p.follow_up_errors()
    if not SECTIONS <= p.text_ids:
        problems.append('missing summary, key evidence, follow-up or full evidence')
    if not p.key_figures <= p.captioned:
        problems.append('key evidence figure needs a descriptive caption')
    if not p.fold_sections <= p.summarized:
        problems.append('folded evidence needs a descriptive summary')
    if p.featured == 0 or p.folded == 0 or p.audit_folds == 0:
        problems.append('expected captioned key evidence and folded full evidence')
    if not any('follow-up' in keys and (dest=='evidence' or 'evidence' in p.ids.get(dest,set()))
               for dest, keys in p.links):
        problems.append('follow-up must link to key evidence')
    for dest, _ in p.links:
        if dest not in p.ids:
            problems.append(f'missing link destination #{dest}')
    if not isinstance(review, dict) or not isinstance(review.get('revision'),str) or not review['revision'].strip():
        return problems + ['missing reviewed revision'], p.images
    sizes = review.get('sizes')
    if not isinstance(sizes,dict) or not sizes:
        return problems + ['missing fit review by size'], p.images
    anchors = set()
    for size, poses in sizes.items():
        if not size.strip() or not isinstance(poses,dict) or len(poses)!=4:
            problems.append(f'{size}: expected four distinct reviewed poses')
            continue
        for pose, methods in poses.items():
            if not pose.strip() or not isinstance(methods,dict) or set(methods)!=CATEGORIES:
                problems.append(f'{size} / {pose}: expected the five categories')
                continue
            for category, detail in methods.items():
                prefix = f'{size} / {pose} / {category}'
                if not isinstance(detail,dict) or detail.get('status')!='pass':
                    problems.append(f'{prefix}: missing passing verdict')
                    continue
                if any(not isinstance(detail.get(f),str) or not detail[f].strip()
                       for f in ('anchor','basis','source')):
                    problems.append(f'{prefix}: missing evidence anchor, basis or source')
                    continue
                anchor = detail['anchor']
                if anchor not in p.figure_ids or anchor in SECTIONS or anchor in anchors:
                    problems.append(f'{prefix}: evidence anchor must point to a distinct folded figure')
                anchors.add(anchor)
    return problems, p.images


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('review', type=Path)
    args=parser.parse_args()
    try:
        issues, count = verify(args.html, json.loads(args.review.read_text(encoding='utf-8')))
    except (OSError,ValueError) as e:
        print(f'FAIL {e}')
        return 1
    if issues:
        print('\n'.join('FAIL '+reason for reason in issues))
        return 1
    print(f'PASS {count} embedded images and fully passing review entries. Browser and evidence review remain required.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
