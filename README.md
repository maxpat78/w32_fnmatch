w32_fnmatch
===========

This package contains an exact Python implementation of the wildcard matching
scheme found in the Windows Command prompt.

The w32_fnmatch.py provides a fnmatch compatible regex translator for use in
Python's standard fnmatch module.

The match_engine.py provides a more traditional algorithm.

Python lacks an MD-DOS compatible wildcard matching engine, and in some
situations this is frustrating.

Surprisingly, the matching algorithm for Long File Names is untouched since
Windows NT 3.1 and its CMD command processor, so this is used here.

Following rules are implemented:

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
easy to say that the command interpreter implements a mix of rules. MSDN says:

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
rules 1-2 and 5-7 like CMD; but ? matches 1 character only, except dot.
