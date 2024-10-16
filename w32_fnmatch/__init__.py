import fnmatch, re

__all__ = ["filter", "fnmatch", "translate"]
__version__ = '1.1'

COPYRIGHT = '''Copyright (C)2012-24, by maxpat78. GNU GPL v2 applies.'''

""" Win32 CMD command prompt (NT 3.1+) wildcards matching algorithm,
implementing the following rules (when the file system supports long names):

   1. * and *.* match all
   2. *. matches all without extension
   3. .* repeated n times matches without or with up to n extensions
   4. ? matches 1 character; 0 or 1 if followed by only wildcards
   5. * matches multiple dots; ? does not (except in NT 3.1)
   6. *.xyz (3 characters ext, even with 1-2 ??) matches any longer xyz ext
   7. [ and ] are valid name characters

According to official sources, the star should match zero or more characters,
and the question mark exactly one.

Reviewing the help for FsRtlIsNameInExpression API in NT kernel, it seems
easy to say that the command interpretr implements a mix of rules. MSDN says:

* (asterisk)            Matches zero or more characters.
? (question mark)       Matches a single character.
DOS_DOT                 Matches either a period or zero characters beyond the name string.
DOS_QM                  Matches any single character or, upon encountering a period or end of name string,
                        advances the expression to the end of the set of contiguous DOS_QMs.
DOS_STAR                Matches zero or more characters until encountering and matching the final . in the
                        name.

In the COMMAND.COM, there are different rules:

   1. * matches all file names without extension
   2. .* matches all extensions
   3. characters after a star are discarded
   4. [ and ] aren't valid in file names
   5. ? follows CMD's rule 4
   6. neither ? nor * matches multiple dots

Under Windows 9x/ME, COMMAND.COM has long file names support and follows
rules 1-2 and 5-7 like CMD; but ? matches 1 character only, except dot. """

def win32_translate(wild):
	"""Translate a Win32 wildcard into a regular expression.
	Implements following rules inducted from DIR behaviour in XP+ Command Prompt:
		* is regex .* when not included in a terminating *.
		a terminating *. means "without extension" and becomes [^.]+
		? is regex [^.] if not followed by wildcards only (until end or the next dot)
		? becomes regex [^.]? if followed by wildcards only
		. followed by wildcards only alternatively matches a base name with or
		without extension, so the regex becomes base$|base.	"""
	def _all_jolly(i, s):
		"Scans a pattern to see if there are only wildcards before dot or end"
		ret = True
		while i < len(s):
			if s[i] == '.': break
			if s[i] not in "*?": ret = False
			i = i+1
		return ret

	i, n = 0, len(wild)
	res = ''
	while i < n:
		c = wild[i]
		if c == '*':
			if i == n-2 and wild[i+1] == '.':
				res = res + '[^.]+'
				break
			else:
				res = res + '.*'
		elif c == '?':
			res = res + '[^.]' # ? doesn't match dot
			if _all_jolly(i+1, wild):
				res = res + '?'
		elif c == '.':
			if i == n-1: break
			if _all_jolly(i+1, wild):
				res = res + '$|%s\\.' % res
			else:
				res = res + '\\.'
		else:
			res = res + re.escape(c)
		i = i+1
	
	if hasattr(win32_translate, 'star_dot_three'):
		# Exception: ending star with 3-chars extension matches all longer extensions
		#~ print('debug: wild=', wild)
		if re.search('\\*.[^.]{3}$', wild):
			res += '[^.]*'

	res = '(?i)^%s$' % res
	#~ print ("debug: wildcard '%s' ==> re '%s'" % (wild, res))
	return res

translate = win32_translate
fnmatch.translate = win32_translate



# Pure (= w/o regex) matching algorithm
def match(s, p, star_dot_three=False):
    class MatchObject:
        pass

    m = MatchObject()
    m.s = s.lower()
    m.p = p.lower()

    m.pi, m.lp = 0, len(p)
    m.si, m.ls = 0, len(s)
    m.p_anchors = []

    def match_loop(m):
        while m.si < m.ls and m.pi < m.lp:
            if m.p[m.pi] == m.s[m.si]:
                # Dot matched not at EOS
                if m.pi + 1 == m.lp and m.p[m.pi] == '.' and m.si < m.ls:
                    break
                m.pi += 1
                m.si += 1
            elif m.p[m.pi] == '?':
                # Dot force to skip a ? sequence
                if m.s[m.si] == '.':
                    while m.pi < m.lp and m.p[m.pi] == '?': m.pi += 1
                m.si += 1
                m.pi += 1
            elif m.p[m.pi] == '*':
                # Record star position to eventually restart search
                m.p_anchors += [(m.pi,)]
                # Skips multiple stars
                while m.pi < m.lp and m.p[m.pi] == '*': m.pi += 1
                # Ending star matches all
                if m.pi == m.lp:
                    m.si = m.ls
                    break
                # Star superseeds question mark
                while m.pi < m.lp and m.p[m.pi] == '?': m.pi += 1
                # Record match start
                m.p_anchors[-1] += (m.si,)
                # Star matches until subexpression is matched
                while m.si < m.ls and m.s[m.si] != m.p[m.pi]: m.si += 1
            elif m.p_anchors:
                # Restarts search from star after last match in string
                m.pi, m.si = m.p_anchors.pop()
                m.si += 1
            else:
                break

    match_loop(m)

    # Repeats loop until other searches are possible
    while m.si < m.ls and m.p_anchors:
        # Dot matched not at EOS
        if m.pi + 1 == m.lp and m.p[m.pi] == '.':
            return False
        if star_dot_three:
            # Exception: *.xyz matches extensions beginning with .xyz, even with 1 or 2 ?
            if m.lp >= 5 and m.ls - m.si < 3 and m.p[-5] == '*' and m.p[-4] == '.' and m.s[m.si-4] == '.':
                return True
        m.pi, m.si = m.p_anchors.pop()
        m.si += 1
        match_loop(m)

    while m.pi < m.lp and (m.p[m.pi] == '*' or m.p[m.pi] == '?' or m.p[m.pi] == '.'): m.pi += 1

    if m.si == m.ls and m.pi < m.lp and m.p[m.pi] == '.':
        # Dot matches EOS only
        if m.pi+1 == m.lp:
            m.pi += 1
        else:
            m.pi += 1
            while m.pi < m.lp and (m.p[m.pi] == '*' or m.p[m.pi] == '?'): m.pi += 1

    # String and pattern both consumed, matches!
    if m.pi == m.lp and m.si == m.ls:
        return True
    else:
        return False
