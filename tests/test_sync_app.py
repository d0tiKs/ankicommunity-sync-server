# -*- coding: utf-8 -*-
import os
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, Mock

import pyzstd
from webob.exc import HTTPBadRequest

from ankisyncd.sync import SYNC_VER
from ankisyncd.sync_app import decode_octet_stream_body
from ankisyncd.sync_app import decompress_zstd_limited
from ankisyncd.sync_app import SyncCollectionHandler
from ankisyncd.sync_app import SyncUserSession

from collection_test_base import CollectionTestBase


class SyncCollectionHandlerTest(CollectionTestBase):
    def setUp(self):
        super().setUp()
        self.session = MagicMock()
        self.session.name = "test"
        self.syncCollectionHandler = SyncCollectionHandler(
            self.collection, self.session
        )

    def tearDown(self):
        CollectionTestBase.tearDown(self)
        self.syncCollectionHandler = None

    def test_old_client(self):
        old = (
            ",".join(("ankidesktop", "2.0.12", "lin::")),
            ",".join(("ankidesktop", "2.0.26", "lin::")),
            ",".join(("ankidroid", "2.1", "")),
            ",".join(("ankidroid", "2.2", "")),
            ",".join(("ankidroid", "2.2.2", "")),
            ",".join(("ankidroid", "2.3alpha3", "")),
        )

        current = (
            None,
            ",".join(("ankidesktop", "2.0.27", "lin::")),
            ",".join(("ankidesktop", "2.0.32", "lin::")),
            ",".join(("ankidesktop", "2.1.0", "lin::")),
            ",".join(("ankidesktop", "2.1.6-beta2", "lin::")),
            ",".join(("ankidesktop", "2.1.9 (dev)", "lin::")),
            ",".join(("ankidesktop", "2.1.26 (arch-linux-2.1.26-1)", "lin:arch:")),
            ",".join(("ankidroid", "2.2.3", "")),
            ",".join(("ankidroid", "2.3alpha4", "")),
            ",".join(("ankidroid", "2.3alpha5", "")),
            ",".join(("ankidroid", "2.3beta1", "")),
            ",".join(("ankidroid", "2.3", "")),
            ",".join(("ankidroid", "2.9", "")),
        )

        for cv in old:
            if not SyncCollectionHandler._old_client(cv):
                raise AssertionError('old_client("%s") is False' % cv)

        for cv in current:
            if SyncCollectionHandler._old_client(cv):
                raise AssertionError('old_client("%s") is True' % cv)

    def test_meta(self):
        meta = self.syncCollectionHandler.meta(v=SYNC_VER)
        self.assertEqual(meta["scm"], self.syncCollectionHandler.scm())
        self.assertTrue((type(meta["ts"]) == int) and meta["ts"] > 0)
        self.assertEqual(meta["mod"], self.collection.mod)
        self.assertEqual(meta["usn"], self.collection.usn())
        self.assertEqual(meta["uname"], self.session.name)
        self.assertEqual(meta["media_usn"], self.collection.media.lastUsn())
        self.assertEqual(meta["musn"], self.collection.media.lastUsn())
        self.assertEqual(meta["msg"], "")
        self.assertEqual(meta["cont"], True)

    def test_meta_legacy_clients_receive_musn(self):
        meta = self.syncCollectionHandler.meta(v=10)
        self.assertEqual(meta["musn"], self.collection.media.lastUsn())
        self.assertEqual(meta["media_usn"], self.collection.media.lastUsn())


class SyncAppTest(unittest.TestCase):
    def test_decode_octet_stream_body_decodes_v11_zstd_json(self):
        body = pyzstd.compress(json.dumps({"foo": "bar"}).encode())
        environ = {"HTTP_ANKI_SYNC": json.dumps({"v": 11, "k": "key", "s": "sess"})}

        decoded = decode_octet_stream_body(body, environ)

        self.assertEqual(decoded["foo"], "bar")
        self.assertEqual(decoded["v"], 11)
        self.assertEqual(decoded["k"], "key")
        self.assertEqual(decoded["s"], "sess")

    def test_decompress_zstd_limited_rejects_oversized_output(self):
        body = pyzstd.compress(b"a" * 128)

        with self.assertRaises(HTTPBadRequest) as ctx:
            decompress_zstd_limited(body, max_output=32)

        self.assertEqual(ctx.exception.detail, "zstd data too large")

    def test_decompress_zstd_limited_rejects_invalid_data(self):
        with self.assertRaises(HTTPBadRequest) as ctx:
            decompress_zstd_limited(b"not zstd", max_output=32)

        self.assertEqual(ctx.exception.detail, "invalid zstd data")
