Lyrics Plugin
=============

The ``lyrics`` plugin fetches and stores song lyrics from databases on the Web.
Namely, the current version of the plugin uses Genius.com_, Tekstowo.pl_,
LRCLIB_, lrcmux_ and, optionally, the Google Custom Search API.

.. _genius.com: https://genius.com/

.. _lrclib: https://lrclib.net/

.. _lrcmux: https://lrcmux.dev/

.. _tekstowo.pl: https://www.tekstowo.pl/

Install
-------

Firstly, enable ``lyrics`` plugin in your configuration (see
:ref:`using-plugins`). Then, install ``beets`` with ``lyrics`` extra

.. code-block:: bash

    pip install "beets[lyrics]"

Fetch Lyrics During Import
--------------------------

When importing new files, beets will now fetch lyrics for files that don't
already have them. The lyrics will be stored in the beets database. The plugin
also sets a few useful flexible attributes:

- ``lyrics_backend``: name of the backend that provided the lyrics
- ``lyrics_url``: URL of the page where the lyrics were found
- ``lyrics_instrumental``: whether the backend marked the track as instrumental
- ``lyrics_language``: original language of the lyrics
- ``lyrics_translation_language``: language of the lyrics translation (if
  translation is enabled)

When a backend reports an instrumental track, beets leaves the lyrics text empty
and sets ``lyrics_instrumental`` instead.

If the ``import.write`` config option is on, then the lyrics will also be
written to the files' tags.

Configuration
-------------

To configure the plugin, make a ``lyrics:`` section in your configuration file.
Default configuration:

.. code-block:: yaml

    lyrics:
        auto: yes
        auto_ignore: null
        translate:
            api_key:
            from_languages: []
            to_language:
        dist_thresh: 0.11
        fallback: null
        force: no
        keep_synced: no
        google_API_key: null
        google_engine_ID: 009217259823014548361:lndtuqkycfu
        lrcmux:
          url: https://api.lrcmux.dev
          sources: []
        print: no
        rest_directory: null
        sources: [lrclib, google, genius, lrcmux]
        synced: no

The available options are:

- **auto**: Fetch lyrics automatically during import.
- **auto_ignore**: A beets query string of items to skip when fetching lyrics
  during auto import. For example, to skip tracks from Bandcamp or with a Techno
  genre:

  .. code-block:: yaml

      lyrics:
        auto_ignore: |
          data_source:bandcamp
          ,
          genres:techno

  Default: ``null`` (nothing is ignored). See :doc:`/reference/query` for the
  query syntax.

- **translate**:

  - **provider**: The translation service to use, ``azure`` or ``deepl``. Not
    case-sensitive. Default: ``azure``. (see :ref:`lyrics-translation`)
  - **api_key**: API key of your Azure Translator resource or of your DeepL
    account. (see :ref:`lyrics-translation`)
  - **from_languages**: By default all lyrics with a language other than
    ``to_language`` are translated. Use a list of language codes to restrict
    them.
  - **to_language**: Language code to translate lyrics to.

- **dist_thresh**: The maximum distance between the artist and title combination
  of the music file and lyrics candidate to consider them a match. Lower values
  will make the plugin more strict, higher values will make it more lenient.
  This does not apply to the ``lrclib`` backend as it matches durations.
- **fallback**: By default, the file will be left unchanged when no lyrics are
  found. Use the empty string ``''`` to reset the lyrics in such a case.
- **force**: By default, beets won't fetch lyrics if the files already have
  ones. To instead always fetch lyrics, set the ``force`` option to ``yes``.
- **keep_synced**: When enabled, tracks that already have synced lyrics are
  skipped even when ``force`` is set. Useful when re-fetching lyrics for a
  library that contains a mix of synced and plain lyrics and you only want to
  fill in the gaps. Default: ``no``.
- **google_API_key**: Your Google API key (to enable the Google Custom Search
  backend).
- **google_engine_ID**: The custom search engine to use. Default: The `beets
  custom search engine`_, which gathers an updated list of sources known to be
  scrapeable.
- **lrcmux**:

  - **url**: Base URL of the lrcmux_ instance to use. Override this to point at
    a self-hosted instance.
  - **sources**: List of lrcmux provider IDs to restrict the search to, e.g.
    ``[ytmusic, kugou]``. Prefix an entry with ``!`` to exclude that provider
    instead, e.g. ``["!musixmatch"]``. Leave empty (the default) to use all
    providers.

- **print**: Print lyrics to the console.
- **rest_directory**: The directory to which reStructuredText_ (ReST) rendered
  lyric documents will be output. See :ref:`rendering-lyrics`.
- **sources**: List of sources to search for lyrics. An asterisk ``*`` expands
  to all available sources. The ``google`` source will be automatically
  deactivated if no ``google_API_key`` is setup. By default, ``musixmatch`` and
  ``tekstowo`` are excluded because they block the beets User-Agent.
- **synced**: Prefer synced lyrics over plain lyrics if a source offers them.
  ``lrclib`` and ``lrcmux`` both provide synced lyrics. Using this option,
  existing synced lyrics are not replaced by newly fetched plain lyrics (even
  when ``force`` is enabled). To allow that replacement, disable ``synced``.
  When synced lyrics are written to an ID3-tagged file (MP3, AIFF, etc.) the
  plugin stores the timestamped data in the ``SYLT`` (synchronized lyrics) frame
  and plain text (without timestamps) in the ``USLT`` (unsynchronized lyrics)
  frame, so players that support only one of the two formats can still show the
  correct lyrics.

.. _beets custom search engine: https://cse.google.com/cse?cx=009217259823014548361:lndtuqkycfu

Fetching Lyrics Manually
------------------------

The ``lyrics`` command provided by this plugin fetches lyrics for items that
match a query (see :doc:`/reference/query`). For example, ``beet lyrics magnetic
fields absolutely cuckoo`` will get the lyrics for the appropriate Magnetic
Fields song, ``beet lyrics magnetic fields`` will get lyrics for all my tracks
by that band, and ``beet lyrics`` will get lyrics for my entire library. The
lyrics will be added to the beets database and, if ``import.write`` is on,
embedded into files' metadata.

The ``-p, --print`` option to the ``lyrics`` command makes it print lyrics out
to the console so you can view the fetched (or previously-stored) lyrics.

The ``-f, --force`` option forces the command to fetch lyrics, even for tracks
that already have lyrics.

The ``--keep-synced`` option skips tracks that already have synced lyrics,
regardless of the ``force`` flag. This is handy when you want to re-fetch plain
lyrics without touching tracks that already have a synced version. Use
``--no-keep-synced`` to override a ``keep_synced: yes`` configuration for a
single command run.

Inversely, the ``-l, --local`` option restricts operations to lyrics that are
locally available, which show lyrics faster without using the network at all.

.. _rendering-lyrics:

Rendering Lyrics into Other Formats
-----------------------------------

The ``-r directory, --write-rest directory`` option renders all lyrics as
reStructuredText_ (ReST) documents in ``directory``. That directory, in turn,
can be parsed by tools like Sphinx_ to generate HTML, ePUB, or PDF documents.

Minimal ``conf.py`` and ``index.rst`` files are created the first time the
command is run. They are not overwritten on subsequent runs, so you can safely
modify these files to customize the output.

Sphinx supports various builders_, see a few suggestions:

.. admonition:: Build an HTML version

    ::

        sphinx-build -b html <dir> <dir>/html

.. admonition:: Build an ePUB3 formatted file, usable on ebook readers

    ::

        sphinx-build -b epub3 <dir> <dir>/epub

.. admonition:: Build a PDF file, which incidentally also builds a LaTeX file

    ::

        sphinx-build -b latex <dir> <dir>/latex && make -C <dir>/latex all-pdf

.. _builders: https://www.sphinx-doc.org/en/master/usage/builders/index.html

.. _restructuredtext: https://sourceforge.net/projects/docutils/

.. _sphinx: https://www.sphinx-doc.org/en/master/

Activate Google Custom Search
-----------------------------

You need to `register for a Google API key
<https://console.cloud.google.com/apis/credentials>`__. Set the
``google_API_key`` configuration option to your key.

Then add ``google`` to the list of sources in your configuration (or use default
list, which includes it as long as you have an API key). If you use default
``google_engine_ID``, we recommend limiting the sources to ``google`` as the
other sources are already included in the Google results.

Optionally, you can `define a custom search engine`_. Get your search engine's
token and use it for your ``google_engine_ID`` configuration option. By default,
beets use a list of sources known to be scrapeable.

Note that the Google custom search API is limited to 100 queries per day. After
that, the lyrics plugin will fall back on other declared data sources.

.. _define a custom search engine: https://programmablesearchengine.google.com/about/

.. _lyrics-translation:

Activate On-the-Fly Translation
-------------------------------

The plugin can translate the lyrics it fetches. Each line is followed by its
translation, and the language is stored in ``lyrics_translation_language``.
Choose the translation service with the ``translate.provider`` option:

- ``azure``: Azure AI Translator. This is the default, so existing
  configurations keep working without changes.
- ``deepl``: DeepL, which has a free plan.

Translation is off until both ``translate.api_key`` and
``translate.to_language`` are set. Lyrics that are already in the target
language are left as they are.

Translate with DeepL
~~~~~~~~~~~~~~~~~~~~

1. Sign up for DeepL API access on the `DeepL website`_. The free plan is enough
   to try the feature.
2. Copy your authentication key from the *API keys* page of your DeepL account.
   Keys of the free plan end in ``:fx``; the plugin uses the free or the paid
   DeepL server to match your key.
3. Set the provider, key and target language in your configuration:

   .. code-block:: yaml

       lyrics:
         translate:
           provider: deepl
           api_key: YOUR_DEEPL_API_KEY
           to_language: de
           from_languages: [en]

4. Fetch lyrics as usual, for example with ``beet lyrics -f QUERY`` to fetch
   them again for tracks that already have lyrics. Lyrics are only translated
   when they are fetched.

You should expect lyrics like this:

::

    Original verse / Ursprünglicher Vers
    Some other verse / Ein anderer Vers

``beet config`` shows ``api_key`` as ``REDACTED``, so you can share its output
without leaking your key. See DeepL's `list of supported languages`_ for the
codes that ``to_language`` accepts.

Translate with Azure
~~~~~~~~~~~~~~~~~~~~

1. `Create a Translator resource`_ on Azure.
       Make sure the region of the translator resource is set to Global. You
       will get 401 unauthorized errors if not. The region of the resource group
       does not matter.
2. `Obtain its API key`_.
3. Add the API key to your configuration as ``translate.api_key``.
4. Configure your target language using the ``translate.to_language`` option.

For example, with the following configuration

.. code-block:: yaml

    lyrics:
      translate:
        api_key: YOUR_TRANSLATOR_API_KEY
        to_language: de

You should expect lyrics like this:

::

    Original verse / Ursprünglicher Vers
    Some other verse / Ein anderer Vers

``provider: azure`` is the default and can be left out.

When translation fails
~~~~~~~~~~~~~~~~~~~~~~

A translation problem never stops the plugin from fetching lyrics. The plugin
logs a warning that says what to fix, and the lyrics are saved without a
translation. The warnings start with the name of the plugin, for example
``lyrics:``.

.. list-table::
    :header-rows: 1
    :widths: 22 48 30

    - - Problem
      - What you see
      - What to do
    - - Setting missing
      - ``Translation is switched off: translate.api_key is not set.`` (or
        ``translate.to_language``, or both)
      - Add the missing option.
    - - Unknown provider
      - ``Translation is switched off: unknown translate.provider 'x'. Choose
        one of: azure, deepl.``
      - Use ``azure`` or ``deepl``.
    - - API key rejected
      - ``The API key was rejected. Check translate.api_key.``
      - Copy the key again. For DeepL, make sure it is an API key.
    - - Quota used up
      - ``The translation quota is used up. Wait for it to reset or use a
        different API key.``
      - Wait for the quota to reset, or use another key.
    - - Language not supported
      - ``The language is not supported. Check translate.to_language and
        translate.from_languages.``
      - Use a language code that your provider supports.
    - - Network problem
      - ``Could not reach DeepL: ... Lyrics are saved untranslated.``
      - Check your connection and fetch the lyrics again.

After a rejected key, a used up quota or an unsupported language, every further
request would fail the same way. The plugin therefore warns once and stops
translating until you restart beets. A network problem only affects the track it
happened on, and the next track is tried again.

To translate the lyrics that were saved without a translation, fix the problem
and run ``beet lyrics -f QUERY``.

.. _create a translator resource: https://learn.microsoft.com/en-us/azure/ai-services/translator/create-translator-resource

.. _deepl website: https://www.deepl.com/pro-api

.. _list of supported languages: https://developers.deepl.com/docs/getting-started/supported-languages

.. _obtain its api key: https://learn.microsoft.com/en-us/python/api/overview/azure/ai-translation-text-readme?view=azure-python&preserve-view=true#get-an-api-key
