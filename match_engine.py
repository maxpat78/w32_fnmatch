import fnmatch, os, re, subprocess, sys

# Non-regex matching algorithm and prompt tester

COPYRIGHT = '''Copyright (C)2012,2020,2024 by maxpat78. GNU GPL v2 applies.'''

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


def match(s, p):
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


if __name__ == '__main__':
    cases = (
('ab[1].c', 'ab[1].c', True), # Win32 must match, [] aren't wildcards
('abc.d', 'AbC.d', True), # Win32 must match, file system is case-insensitive
('ab', 'ab?', True), # 0|1 char
('ac', 'a?c', False), # 1 char
('abc', 'a??c', False), # 2 chars
('abcd', 'a??c', False), # 2 chars
('abcc', 'a??c', True), # 2 chars
('abc', '*.', True), # no ext
('abc.d', '*.', False),
('abc.d', '*.*d', True), # ext ending in "d"
('ab.cd', '*.*d', True),
('abc', '*.*', True), # with ext or not
('abc.d', '*.*', True),
('abc', '*ab.*', False),
('abc', '*abc.*', True),
('abc', '*.?', True),
('abc.d', '*.*', True),
('abc.d', '*.?', True),
('ab', 'a????', True), # a + 0-4 chars
('abcde', 'a????', True), # a + 0-4 chars
('ab', 'a????.??', True), # a + 0-4 chars, w/ or w/o ext of 1-2 chars
('ab', '?a????', False),
('ab.c', 'a????.??', True),
('ab.cd', 'a????.??', True),
('ab.cde', 'a????.??', False),
('ab.c', 'ab.?', True), # w/o ext or w/ 1 char ext
('abc', 'ab.?', False),
('ab', 'ab.?', True),
('ab.ca', 'ab.?a', True), # w/ 2 chars ext ending in a
('ab', 'ab.?a', False),
('abcdef.ghi', 'ab*.???', True),
('abcdef.ghi', 'abc???.???', True),
('abcdef.ghi', 'abcdef.?h?', True),
('abcdef.ghi', 'abcdef.?g?', False),
('abcdef.ghi', 'abcdef.*', True),
('abcdef.ghi', '*abc*', True),
('abcdef.ghi', '*abc*.*', True),
('abcdef.ghi', '*abc*.*hi', True),
('abcdef.ghi', '*abc*.*hj', False),
('abcdef.ghi', '*f*.gh?', True),
('ab.ca', 'ab.*', True), # any ext
('b...txt', 'b*.txt', True), # b with anything ending in .txt
('b...txt', 'b??.txt', False), # it seems logic, but doesn't work at the Prompt!
('b....txt', 'b...txt', False),
('minilj.txt', '*.ini', False),
('abcde.fgh', 'abc*.', False),
('abcde', 'abc*.', True),
('abcde', 'ab*e', True),
('abc', 'ab*e', False),
('abc', 'abc.*', True),
('abc.de.fgh', 'abc.*', True),
('abc.de.fgh', 'abc.*.*', True),
('abc.de.fgh', 'abc.??.*', True),
('abc.fgh', 'abc.*.*', True),
('abc.fgh', 'abc.*.', True),
('abc.fgh', 'abc.*..', True),
('abcfgh', 'abc.*.*', False),
('abc.de.fgh', '*.de.f*', True),
('abc.de.fgh', '*de.f*', True),
('abc.de.fgh', '*f*', True),
('abc..de...fgh', '*de*f*', True),
('abc..de...fgh', 'abc..de.*fgh', True),
('abc.d', '***?*', True),
('abc.d.e', '*.e', True), # with ending .e ext
('abc.e.ef', '*.e', False),
('abc.e.e', '*.e', True),
('abc.e.ef', '*.e*', True), # with .e ext
('abc.e.e', '*.e*', True),
('abc.e.effe', '*.e*e', True),
('abcde.fgh', '*.fgh', True),
#~ ('abcde.fghi', '*.fgh', True), # Prompt says TRUE!!!
#~ ('abcde.fghi', '*.fg?', True), # And so here!
#~ ('abcde.fghi', '*.?gh', True), # And so here!
#~ ('abcde.fghi', '*.f??', True), # And so here!
#~ ('abcde.fghil', 'abc??*.fgh', True), # And so here!
('abcde.fghi', '*.fgh', False), # Win11 fixed this and next 4
('abcde.fghi', '*.fg?', False),
('abcde.fghi', '*.?gh', False),
('abcde.fghi', '*.f??', False),
('abcde.fghil', 'abc??*.fgh', False),
('abcde.fghi', '*.f???', True),
('abcde.fghil', 'abc??*.fgh??', True),
('abcde.fghi', 'abc??.fgh', False), # Here Prompt works!!!
('abcde.fghil', '*.fghi', False), # Here too...
('abcde.fgh.fgh', '*.fgh', True),
('abcde.fgh.fg', '*.fgh', False),
('abcde.fg.fgh', '*.fgh', True),
#~ ('abcde.fghabc.fghab', '*.fgh', True), # And here!
('abcde.fghabc.fghab', '*.fgh', False), # new Win11 behavior
('abcde.fg.fgh.fgho', '*.fghi', False),
('abcde.fg.fgh.fgho', '*.fgh?', True),
    )

    failed = 0

    for case in cases:
##            r = win32_wild_match(case[0], case[1])
            r = match(case[0], case[1])
            if r != case[2]:
                    failed += 1
                    print ("'%s' ~= '%s' is %s, expected %s" % (case[0], case[1], r, case[2]))
    if failed:
            print ("%d/%d self tests failed!" % (failed, len(cases)))
    else:
            print ("All %d self tests passed!" % len(cases))

##    sys.exit()
# Test Command Prompt behaviour
failed = 0
for case in cases:
    if not os.path.exists(case[0]): open(case[0], 'w')
# DIR behaviour
    s = b''
    try:
        s = subprocess.check_output(['cmd', '/c', 'dir', case[1]], stderr=subprocess.STDOUT, shell=True)
    except:
        pass
    Match = re.search('(?im)%s\r'%re.escape(case[0]), s.decode('mbcs')) != None
    if Match != case[2]:
        print ("!!! Check case %s: DIR returned\n%s" % (str(case), s.decode('mbcs')))
        failed+=1

# FOR behaviour
    s = b''
    try:
        s = subprocess.check_output('cmd /c for %%f in (%s) do @echo %%f'%case[1], stderr=subprocess.STDOUT, shell=True)
    except:
        pass
    Match = re.search('(?im)%s\r'%re.escape(case[0]), s.decode('mbcs')) != None
    if Match != case[2]:
        print ("!!! Check case %s: FOR returned\n%s" % (str(case), s.decode('mbcs')))
        failed+=1

# COPY behaviour
    s = b''
    try:
        s = subprocess.check_output('cmd /c copy %s NUL:'%case[1], stderr=subprocess.STDOUT, shell=True)
    except:
        pass
    Match = re.search('%s'%'1 file', s.decode('mbcs')) != None
    if Match != case[2]:
        print ("!!! Check case %s: COPY returned\n%s" % (str(case), s.decode('mbcs')))
        failed+=1

    os.remove(case[0])

if failed:
        print ("%d/%d command prompt tests failed!" % (failed, len(cases)))
else:
        print ("All %d command prompt tests passed!" % len(cases))
