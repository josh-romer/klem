# Only the pinned 무정 sections are supported; this is not a general wiki parser.
# Remove non-nested metadata templates, trim section edges, retain prose/spacing.
gsub("\\{\\{[^{}]*\\}\\}"; "")
| gsub("^\\s+|\\s+$"; "")
| if test("\\[\\[|\\]\\]|\\{\\{|\\}\\}|<|>")
  then error("unexpected remaining markup in pinned novel section") else . end
