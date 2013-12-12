# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2012 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Pitch manipulation.
"""

from __future__ import unicode_literals

import re
from fractions import Fraction

import ly.lex.lilypond


pitchInfo = {
    'nederlands': (
        ('c','d','e','f','g','a','b'),
        ('eses', 'eseh', 'es', 'eh', '', 'ih','is','isih','isis'),
        (('ees', 'es'), ('aes', 'as'))
    ),
    'english': (
        ('c','d','e','f','g','a','b'),
        ('ff', 'tqf', 'f', 'qf', '', 'qs', 's', 'tqs', 'ss'),
    ),
    'deutsch': (
        ('c','d','e','f','g','a','h'),
        ('eses', 'eseh', 'es', 'eh', '', 'ih','is','isih','isis'),
        (('ees', 'es'), ('aes', 'as'), ('hes', 'b'))
    ),
    'svenska': (
        ('c','d','e','f','g','a','h'),
        ('essess', '', 'ess', '', '', '','iss','','ississ'),
        (('ees', 'es'), ('aes', 'as'), ('hess', 'b'))
    ),
    'italiano': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', 'bsb', 'b', 'sb', '', 'sd', 'd', 'dsd', 'dd')
    ),
    'espanol': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', '', 'b', '', '', '', 's', '', 'ss')
    ),
    'portugues': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', 'btqt', 'b', 'bqt', '', 'sqt', 's', 'stqt', 'ss')
    ),
    'vlaams': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', '', 'b', '', '', '', 'k', '', 'kk')
    ),
}
pitchInfo['norsk'] = pitchInfo['deutsch']
pitchInfo['suomi'] = pitchInfo['deutsch']
pitchInfo['catalan'] = pitchInfo['italiano']


class PitchNameNotAvailable(Exception):
    """Exception raised when there is no name for a pitch.
    
    Can occur when translating pitch names, if the target language e.g.
    does not have quarter-tone names.
    
    """
    def __init__(self, language):
        super(PitchNameNotAvailable, self).__init__()
        self.language = language


class Pitch(object):
    """A pitch with note, alter and octave attributes.
    
    Attributes may be manipulated directly.
    
    """
    def __init__(self, note=0, alter=0, octave=0):
        self.note = note        # base note (c, d, e, f, g, a, b)
                                # as integer (0 to 6)
        self.alter = alter      # # = .5; b = -.5; natural = 0
        self.octave = octave    # '' = 2; ,, = -2
    
    def __repr__(self):
        return '<Pitch {0}>'.format(self.output())
    
    def output(self, language="nederlands"):
        """Returns our string representation."""
        return (
            pitchWriter(language)(self.note, self.alter) +
            octaveToString(self.octave))
        
    @classmethod
    def c1(cls):
        """Returns a pitch c'."""
        return cls(octave=1)

    @classmethod
    def c0(cls):
        """Returns a pitch c."""
        return cls()

    def copy(self):
        """Returns a new instance with our attributes."""
        return self.__class__(self.note, self.alter, self.octave)
        
    def makeAbsolute(self, lastPitch):
        """Makes ourselves absolute, i.e. sets our octave from lastPitch."""
        self.octave += lastPitch.octave - (self.note - lastPitch.note + 3) // 7
        
    def makeRelative(self, lastPitch):
        """Makes ourselves relative, i.e. changes our octave from lastPitch."""
        self.octave -= lastPitch.octave - (self.note - lastPitch.note + 3) // 7


class PitchWriter(object):
    language = "unknown"
    def __init__(self, names, accs, replacements=()):
        self.names = names
        self.accs = accs
        self.replacements = replacements

    def __call__(self, note, alter = 0):
        """
        Returns a string representing the pitch in our language.
        Raises PitchNameNotAvailable if the requested pitch
        has an alteration that is not available in the current language.
        """
        pitch = self.names[note]
        if alter:
            acc = self.accs[int(alter * 4 + 4)]
            if not acc:
                raise PitchNameNotAvailable(self.language)
            pitch += acc
        for s, r in self.replacements:
            if pitch.startswith(s):
                pitch = r + pitch[len(s):]
                break
        return pitch


class PitchReader(object):
    def __init__(self, names, accs, replacements=()):
        self.names = list(names)
        self.accs = list(accs)
        self.replacements = replacements
        self.rx = re.compile("({0})({1})?$".format("|".join(names),
            "|".join(acc for acc in accs if acc)))

    def __call__(self, text):
        for s, r in self.replacements:
            if text.startswith(r):
                text = s + text[len(r):]
        for dummy in 1, 2:
            m = self.rx.match(text)
            if m:
                note = self.names.index(m.group(1))
                if m.group(2):
                    alter = Fraction(self.accs.index(m.group(2)) - 4, 4)
                else:
                    alter = 0
                return note, alter
            # HACK: were we using (rarely used) long english syntax?
            text = text.replace('flat', 'f').replace('sharp', 's')
        return False
            
            
def octaveToString(octave):
    """Converts numeric octave to a string with apostrophes or commas.
    
    0 -> "" ; 1 -> "'" ; -1 -> "," ; etc.
    
    """
    return octave < 0 and ',' * -octave or "'" * octave


def octaveToNum(octave):
    """Converts string octave to an integer:
    
    "" -> 0 ; "," -> -1 ; "'''" -> 3 ; etc.
    
    """
    return octave.count("'") - octave.count(",")


_pitchReaders = {}
_pitchWriters = {}


def pitchReader(language):
    """Returns a PitchReader for the speficied language."""
    try:
        return _pitchReaders[language]
    except KeyError:
        res = _pitchReaders[language] = PitchReader(*pitchInfo[language])
        return res


def pitchWriter(language):
    """Returns a PitchWriter for the speficied language."""
    try:
        return _pitchWriters[language]
    except KeyError:
        res = _pitchWriters[language] = PitchWriter(*pitchInfo[language])
        res.language = language
        return res


class PitchIterator(object):
    """Iterate over notes or pitches in a source."""
    
    def __init__(self, source):
        """Initialize with a ly.document.Source.
        
        The language is set to "nederlands".
        
        """
        self.source = source
        self.setLanguage("nederlands")
    
    def setLanguage(self, lang):
        """Changes the pitch name language to use.
        
        Called internally when \language or \include tokens are encoutered
        with a valid language name/file.
        
        Sets the language attribute to the language name and the read attribute
        to an instance of ly.pitch.PitchReader.
        
        """
        if lang in pitchInfo.keys():
            self.language = lang
            return True
    
    def tokens(self):
        """Yield all the tokens from the source, following the language."""
        import ly.lex.lilypond
        for t in self.source:
            yield t
            if isinstance(t, ly.lex.lilypond.Keyword):
                if t in ("\\include", "\\language"):
                    for t in self.source:
                        if not isinstance(t, ly.lex.Space) and t != '"':
                            lang = t[:-3] if t.endswith('.ly') else t[:]
                            if self.setLanguage(lang):
                                yield LanguageName(lang, t.pos)
                            break
                        yield t
    
    def read(self, token):
        """Reads the token and returns (note, alter) or None."""
        return pitchReader(self.language)(token)
    
    def pitches(self):
        """Yields all tokens, but collects Note and Octave tokens.
        
        When a Note is encoutered, also reads octave and octave check and then
        a Pitch is yielded instead of the tokens.
        
        """
        tokens = self.tokens()
        for t in tokens:
            while isinstance(t, ly.lex.lilypond.Note):
                p = self.read(t)
                if not p:
                    break
                p = Pitch(*p)
                
                p.noteToken = t
                p.octave = 0
                p.origOctave = 0
                p.octaveSlice = slice(t.end, t.end)
                p.octaveCheck = None
                p.origOctaveCheck = None
                p.octaveCheckSlice = None
                
                t = None # prevent hang in this loop
                for t in tokens:
                    if isinstance(t, ly.lex.lilypond.Octave):
                        p.octave = p.origOctave = octaveToNum(t)
                        p.octaveSlice = slice(t.pos, t.end)
                    elif isinstance(t, ly.lex.lilypond.OctaveCheck):
                        p.octaveCheck = p.origOctaveCheck = octaveToNum(t)
                        p.octaveCheckSlice = slice(t.pos, t.end)
                        break
                    elif not isinstance(t, (ly.lex.Space, ly.lex.lilypond.Accidental)):
                        break
                yield p
                if t is None:
                    break
            else:
                yield t
        
    def position(self, t):
        """Returns the cursor position for the given token or Pitch."""
        if isinstance(t, Pitch):
            return t.noteToken.pos
        else:
            return t.pos
    
    def write(self, pitch, document, language=None):
        """Output a changed Pitch to the ly.document.Document."""
        pwriter = pitchWriter(language or self.language)
        note = pwriter(pitch.note, pitch.alter)
        if note != pitch.noteToken:
            document[pitch.noteToken.pos:pitch.noteToken.end] = note
        if pitch.octave != pitch.origOctave:
            document[pitch.octaveSlice] = octaveToString(pitch.octave)
        if pitch.origOctaveCheck is not None:
            if pitch.octaveCheck is None:
                del document[pitch.octaveCheckSlice]
            else:
                octaveCheck = '=' + octaveToString(pitch.octaveCheck)
                document[pitch.octaveCheckSlice] = octaveCheck


class LanguageName(ly.lex.Token):
    """A Token that denotes a language name."""
    pass


