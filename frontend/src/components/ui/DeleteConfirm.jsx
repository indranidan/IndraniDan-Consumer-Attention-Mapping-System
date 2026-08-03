/**
 * DeleteConfirm Component
 * ========================
 * Reusable delete confirmation dialog.
 */

import Modal from "./Modal";

export default function DeleteConfirm({ isOpen, onClose, onConfirm, title, message, loading }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title || "Confirm Delete"} maxWidth="max-w-md">
      <div className="text-center py-2">
        <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
          <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </div>
        <p className="text-sm text-gray-300 mb-6">
          {message || "This action cannot be undone. Are you sure you want to proceed?"}
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 transition-all disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-red-600 hover:bg-red-500 transition-all disabled:opacity-50 flex items-center gap-2"
          >
            {loading && (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            Delete
          </button>
        </div>
      </div>
    </Modal>
  );
}
