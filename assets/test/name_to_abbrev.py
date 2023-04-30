# United States of America Python Dictionary to translate States,
# Districts & Territories to Two-Letter codes and vice versa.
#
# https://gist.github.com/rogerallen/1583593
#
# Dedicated to the public domain.  To the extent possible under law,
# Roger Allen has waived all copyright and related or neighboring
# rights to this code.

name_to_abbrev = { f"{x}_Name": x for x in "ABCDEFGHIJ" }

# thank you to @kinghelix and @trevormarburger for this idea
abbrev_to_name = dict(map(reversed, name_to_abbrev.items()))
