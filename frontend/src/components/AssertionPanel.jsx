import React, { useState } from 'react';
import { Database, Plus, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function AssertionPanel({ tables, setTables }) {
  const [newTable, setNewTable] = useState('');

  const handleAddTable = (e) => {
    e.preventDefault();
    const val = newTable.trim();
    if (val && !tables.includes(val)) {
      setTables([...tables, val]);
      setNewTable('');
    }
  };

  const handleRemoveTable = (tableToRemove) => {
    setTables(tables.filter(t => t !== tableToRemove));
  };

  return (
    <motion.div 
      className="glass-panel"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--secondary-color)' }}>
          <Database size={22} />
          目标路由基础表
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          定义你需要自动化比对的原始基础表名（请勿带分库分表号后缀）。
        </p>
      </div>

      <form onSubmit={handleAddTable} style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <input
          type="text"
          className="input-field"
          placeholder="例如: tb_dpmst_medium"
          value={newTable}
          onChange={(e) => setNewTable(e.target.value)}
        />
        <button type="submit" className="btn btn-secondary" style={{ padding: '0 16px' }}>
          <Plus size={20} />
        </button>
      </form>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {tables.length === 0 ? (
          <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
            暂未添加任何需要核验的基础表。
          </div>
        ) : (
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <AnimatePresence>
              {tables.map((table) => (
                <motion.li
                  key={table}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-sm)'
                  }}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px' }}>{table}</span>
                  <button 
                    onClick={() => handleRemoveTable(table)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--error)', cursor: 'pointer', padding: '4px' }}
                  >
                    <Trash2 size={16} />
                  </button>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </motion.div>
  );
}
