"""Shared canonicalization: archive HTML and hand-made CSV land in the same space."""
import re, math, hashlib, unicodedata
from html.parser import HTMLParser

VOID = {'img','hr','input','meta','link','source','wbr','area','base','col','param','track'}
SPAN_KIND = {'quote':'green','orangeQuote':'orange','heading':'red','spoiler':'spoiler'}
TAG_KIND  = {'em':'italics','i':'italics','strong':'bold','b':'bold',
             'u':'underline','s':'strike','pre':'code'}
KNOWN  = {'a','br','span','em','strong','u','s','pre','code','b','i','small'}
STRUCT = {'ol','ul','li','div','p','blockquote','table','tbody','tr','td','th',
          'h1','h2','h3','h4','h5','h6'}
DELIM_TAGS = {'spoiler','red','code','bold','italics','underline','strike'}
BOARD_PATH = re.compile(r'^/[^/]+/(?:index\.html)?$')

CSV_ESC = re.compile(r'\\r\\n|\\r|\\n|\\t|\\\\')
CSV_MAP = {r'\r\n': '\n', r'\r': '\n', r'\n': '\n', r'\t': '\t', r'\\': '\\'}

def unescape_csv(t):
    """CSV-side only. Literal escape sequences -> real characters.
    Single pass so an escaped backslash is never re-processed."""
    return CSV_ESC.sub(lambda m: CSV_MAP[m.group(0)], t)

def cf_decode(href):
    try:
        b = bytes.fromhex(href.split('#',1)[-1])
        return ''.join(chr(c ^ b[0]) for c in b[1:])
    except Exception:
        return ''

def link_kind(href, attrs):
    if attrs.get('target') == '_blank':          return 'url'
    if href.startswith('mailto:'):               return 'email'
    if '/cdn-cgi/l/email-protection' in href:    return 'email'
    if href.startswith('/') and '/res/' in href: return 'ref'
    if BOARD_PATH.match(href):                   return 'boardref'
    return 'otherlink'

class BodyExtractor(HTMLParser):
    """Suppression is DERIVED from the stack, never a separate counter."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks, self.counts, self.links, self.tags = [], {}, [], {}
        self.ctx, self.literal = [], set()
        self.malformed = 0
    def _bump(self,k,n=1): self.counts[k]=self.counts.get(k,0)+n
    def _dropping(self): return any(k=='drop' for k,_ in self.ctx)
    def _close(self, tag):
        for i in range(len(self.ctx)-1,-1,-1):
            if self.ctx[i][1]==tag:
                del self.ctx[i:]; return True
        return False
    def handle_starttag(self, tag, attrs):
        self.tags[tag]=self.tags.get(tag,0)+1
        a=dict(attrs)
        if tag in ('script','style'):
            self.ctx.append(('drop',tag)); return
        if tag=='br':
            self.chunks.append('\n'); self._bump('br'); return
        if tag in VOID: return
        if tag=='li':
            self.chunks.append('\n'); self.ctx.append(('other',tag)); return
        if tag in STRUCT:
            self.ctx.append(('other',tag)); return
        if tag=='a':
            if self.ctx and self.ctx[-1][1]=='a': del self.ctx[-1:]   # unclosed <a>
            href=a.get('href') or ''
            kind=link_kind(href,a)
            if kind=='otherlink':
                self.ctx.append(('other',tag)); return
            self.chunks.append('<%s>'%kind); self._bump(kind)
            self.links.append((kind, cf_decode(href)
                               if kind=='email' and '#' in href else href))
            self.ctx.append(('drop',tag)); return
        if tag in KNOWN:
            if tag=='span':
                cls=(a.get('class') or '').split()
                k=next((SPAN_KIND[c] for c in cls if c in SPAN_KIND),'other')
            else:
                k=TAG_KIND.get(tag,'other')
            if k!='other': self._bump(k)
            self.ctx.append((k,tag)); return
        self.chunks.append(self.get_starttag_text() or '')
        self.literal.add(tag); self._bump('literal_tag')
    def handle_startendtag(self, tag, attrs):
        if tag in KNOWN or tag in STRUCT or tag in VOID or tag in ('br','script','style'):
            self.handle_starttag(tag,attrs)
            if tag not in VOID and tag!='br': self.handle_endtag(tag)
        else:
            self.tags[tag]=self.tags.get(tag,0)+1
            self.chunks.append(self.get_starttag_text() or ''); self._bump('literal_tag')
    def handle_endtag(self, tag):
        if not self._close(tag) and tag in self.literal:
            self.chunks.append('</%s>'%tag)
    def handle_data(self, d):
        if self._dropping(): return
        self.chunks.append(d)
        if any(k=='code' for k,_ in self.ctx): self._bump('code_chars',len(d))
    def close(self):
        super().close()
        if self.ctx: self.malformed=len(self.ctx); self.ctx=[]

def html_to_text(body):
    p=BodyExtractor(); p.feed(body or ''); p.close()
    return ''.join(p.chunks), p

def fix_newlines(t): return t.replace('\r\n','\n').replace('\r','\n')

BOARDREF = re.compile(r'>>>/[^\s/<>]+/\d*')
REF      = re.compile(r'>>\d+')
URL = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+"
    r"|\b[a-z0-9][a-z0-9-]{0,61}\."
    r"(?:com|net|org|io|gg|me|co|ru|su|xyz|top|cc|info|biz|site|online|club|link"
    r"|live|fun|space|onion|to|ly|gl|tv|sh|pw|dev|app|pro|one|wiki|art|uk|de|fr"
    r"|nl|pl|eu|in|is|it|im|be)\b(?:/[^\s<>\"']*)?", re.I)

def mask(t): return URL.sub('<url>', REF.sub('<ref>', BOARDREF.sub('<boardref>', t)))

ZW = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00ad]')
CONFUSE = str.maketrans({
    'а':'a','е':'e','о':'o','р':'p','с':'c','у':'y','х':'x','і':'i','ј':'j',
    'ѕ':'s','ԁ':'d','һ':'h','α':'a','ο':'o','ρ':'p','τ':'t','υ':'y','χ':'x','ν':'v'})

def fold(t):
    t=ZW.sub('',t)
    t=unicodedata.normalize('NFKC',t)
    t=''.join(c for c in unicodedata.normalize('NFD',t)
              if unicodedata.category(c)!='Mn')
    return t.casefold().translate(CONFUSE)

def collapse(t): return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9]+',' ',fold(t))).strip()
def squeeze(t):  return re.sub(r'[^a-z0-9]+','',fold(t))

def squeeze_key(sq, post_id=None):
    if not sq: sq='post:%s'%post_id
    h=hashlib.md5(sq.encode('utf-8')).hexdigest()
    return int(h[:16],16), int(h[16:24],16)%100

def shape_features(t):
    n=max(len(t),1)
    letters=sum(c.isalpha() for c in t); alnum=sum(c.isalnum() for c in t)
    toks=t.split() or ['']
    runs=len(re.findall(r'[^\W\d_][^\w\s]{1,3}[^\W\d_]',t))
    cnt={}
    for c in t: cnt[c]=cnt.get(c,0)+1
    ent=-sum((v/n)*math.log2(v/n) for v in cnt.values())
    return [(n-alnum)/n, t.count('*')/n, t.count(' ')/max(letters,1),
            sum(len(x)==1 for x in toks)/len(toks),
            sum(len(x) for x in toks)/len(toks), runs/n,
            sum(c.isdigit() for c in t)/n, t.count('<url>'), min(n,500)/500, ent]
