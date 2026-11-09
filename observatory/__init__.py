"""Observatory: a read-only viewer that streams or exports one run for the web front end.

Kept outside `mlab/` because the builder's sandbox can read `mlab/` (D-023): the viewer's
endpoints and token file location are no business of either agent.
"""
