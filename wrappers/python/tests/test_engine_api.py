"""Native 0.7 metadata and storage ABI tests without loading an engine."""

import ctypes
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mist


def output_function(value):
    data = value.encode('utf-8')

    def read(buffer, size):
        if size >= len(data):
            ctypes.memmove(buffer, data, len(data))
        return len(data)

    return Mock(side_effect=read)


class EngineApiTests(unittest.TestCase):
    def setUp(self):
        self.node = mist.MistNode.__new__(mist.MistNode)
        self.node.lib = Mock()

    def test_metadata_queries_size_then_reads_exact_utf8_bytes(self):
        info = json.dumps({'version': '0.7.0', 'target': '日本語', 'extra': 'x' * 8192}, ensure_ascii=False)
        for name, value in [('get_version', '0.7.0'), ('get_build_info', info)]:
            with self.subTest(name=name):
                fn = output_function(value)
                setattr(self.node.lib, name, fn)
                self.assertEqual(getattr(self.node, name)(), value)
                self.assertEqual(fn.call_args_list[0].args, (None, 0))
                self.assertEqual(fn.call_args_list[1].args[1], len(value.encode('utf-8')))
                self.assertEqual(fn.call_count, 2)

    def test_module_metadata_does_not_create_a_node(self):
        lib = self.node.lib
        lib.get_version = output_function('0.7.0')
        lib.get_build_info = output_function('{"version":"0.7.0"}')
        with patch('mist.core.os.path.exists', return_value=True), \
             patch('mist.core.ctypes.CDLL', return_value=lib), \
             patch('mist.core._active_instance', None):
            self.assertEqual(mist.get_version(), '0.7.0')
            self.assertEqual(json.loads(mist.get_build_info()), {'version': '0.7.0'})
            self.assertIsNone(mist.core._active_instance)
        for fn in (lib.get_version, lib.get_build_info):
            self.assertEqual(fn.argtypes, [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t])
            self.assertEqual(fn.restype, ctypes.c_uint32)
        lib.init.assert_not_called()
        lib.init_with_config.assert_not_called()

    def test_metadata_does_not_read_beyond_allocated_buffer(self):
        self.node.lib.get_build_info.side_effect = [2, 100]
        with self.assertRaisesRegex(RuntimeError, 'grew'):
            self.node.get_build_info()

    def test_storage_size_query_and_binary_data(self):
        def read(cid, cid_len, buffer, size):
            self.assertEqual((cid, cid_len), (b'cid', 3))
            if size >= 3:
                ctypes.memmove(buffer, b'\x00\xff\x01', 3)
            return 3

        self.node.lib.storage_get.side_effect = read
        self.assertEqual(self.node.storage_get('cid'), b'\x00\xff\x01')
        self.assertEqual(self.node.lib.storage_get.call_args_list[0].args, (b'cid', 3, None, 0))
        self.node.lib.storage_get.side_effect = [2, 3]
        self.assertIsNone(self.node.storage_get('cid'))
        self.node.lib.storage_get.side_effect = [0]
        self.assertIsNone(self.node.storage_get('cid'))

    def test_storage_add_at_argument_order_and_failure(self):
        def add(name, name_len, data, data_len, x, y, z, buffer, size):
            self.assertEqual((name, name_len, data, data_len, x, y, z),
                             ('名前'.encode(), 6, b'\x00\xff', 2, 1.0, 2.0, 3.0))
            ctypes.memmove(buffer, b'cid', 3)
            return 3

        self.node.lib.storage_add_at.side_effect = add
        self.assertEqual(self.node.storage_add_at('名前', b'\x00\xff', 1, 2, 3), 'cid')
        self.node.lib.storage_add.return_value = 0
        with self.assertRaises(RuntimeError):
            self.node.storage_add('name', b'data')


if __name__ == '__main__':
    unittest.main()
