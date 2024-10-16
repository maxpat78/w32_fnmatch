import unittest
from w32_fnmatch import fnmatch, match

class w32fnmatch(unittest.TestCase):
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
	('abcde.fghi', 'abc??.fgh', False), # Here Prompt works!!!
	('abcde.fghil', '*.fghi', False), # Here too...
	('abcde.fgh.fgh', '*.fgh', True),
	('abcde.fgh.fg', '*.fgh', False),
	('abcde.fg.fgh', '*.fgh', True),
	('abcde.fg.fgh.fgho', '*.fghi', False),
	('abcde.fg.fgh.fgho', '*.fgh?', True),
		)

	new_cases = (
		('abcde.fghi', '*.fgh', True),
		('abcde.fghi', '*.fg?', True),
		('abcde.fghi', '*.?gh', True),
		('abcde.fghi', '*.f??', True),
		('abcde.fghil', 'abc??*.fgh', True),
		('abcde.fghabc.fghab', '*.fgh', True),
	)
	
	def test_0(p):
		failed = 0
		for case in p.cases:
			r = fnmatch.fnmatch(case[0], case[1])
			if r != case[2]:
				failed += 1
				print ("'%s' ~= '%s' is %s, expected %s" % (case[0], case[1], r, case[2]))
		if failed:
			print ("%d/%d base fnmatch tests failed!" % (failed, len(p.cases)))
		else:
			print ("All base %d fnmatch tests passed!" % len(p.cases))

	def test_1(p):
		fnmatch.translate.star_dot_three = 1
		fnmatch._compile_pattern.cache_clear() # purge re cache, since some regexes change here!
		failed = 0
		for case in p.new_cases:
			r = fnmatch.fnmatch(case[0], case[1])
			if r != case[2]:
				failed += 1
				print ("'%s' ~= '%s' is %s, expected %s" % (case[0], case[1], r, case[2]))
		if failed:
			print ("%d/%d extended fnmatch tests failed!" % (failed, len(p.new_cases)))
		else:
			print ("All extended fnmatch %d tests passed!" % len(p.new_cases))

	def test_2(p):
		failed = 0
		for case in p.cases:
			r = match(case[0], case[1])
			if r != case[2]:
				failed += 1
				print ("'%s' ~= '%s' is %s, expected %s" % (case[0], case[1], r, case[2]))
		if failed:
			print ("%d/%d base match tests failed!" % (failed, len(p.cases)))
		else:
			print ("All base %d match tests passed!" % len(p.cases))

	def test_3(p):
		failed = 0
		for case in p.new_cases:
			r = match(case[0], case[1], 1)
			if r != case[2]:
				failed += 1
				print ("'%s' ~= '%s' is %s, expected %s" % (case[0], case[1], r, case[2]))
		if failed:
			print ("%d/%d extended match tests failed!" % (failed, len(p.new_cases)))
		else:
			print ("All extended %d match tests passed!" % len(p.new_cases))



if __name__ == '__main__':
	unittest.main()
