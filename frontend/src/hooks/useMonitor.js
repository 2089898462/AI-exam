/**
 * 考试监考 Hook
 *
 * 功能：
 * - 监听页面可见性变化（visibilitychange）和窗口焦点变化（blur/focus）
 * - 统计页面离开次数和累计离开时长
 * - 事件合并机制：防止 visibilitychange 和 blur 同时触发导致重复统计
 * - pagehide/pageshow 兼容：覆盖 iOS Safari 后台切换场景
 * - 时间戳去重：防止多事件源（visibilitychange + pagehide + blur）重复触发
 * - S8.4.1: 环境采集（设备/屏幕/网络/浏览器信息）
 * - S8.4.1: 横竖屏检测（orientationchange）
 * - S8.4.1: 网络状态检测（online/offline）
 * - S8.4.1: 刷新检测（pageshow.persisted bfcache）
 * - S8.4.4: sessionStorage 持久化（key: exam_monitor_{recordId}）
 *   - 事件变化实时写入，页面刷新/浏览器回收后恢复
 *   - 隐藏状态被终止时生成 leave_recovered 补偿事件
 *   - 提交成功后由页面调用 clearPersistedData 清除
 *
 * 使用：
 *   const monitor = useMonitor()
 *   monitor.startMonitoring(recordId) // 考试开始时调用（传入记录ID用于缓存隔离）
 *   monitor.stopMonitoring()          // 考试结束/页面销毁时调用
 *   const data = monitor.flushEvents() // 提交前获取监考数据
 *   monitor.clearPersistedData()       // 提交成功后清除缓存
 */

import { ref, onBeforeUnmount } from 'vue';

// 事件合并时间窗口（毫秒）
// S8.4.3-d: 从 300ms 缩短到 100ms，减少移动端切屏延迟
const MERGE_WINDOW = 100;
// 时间戳去重窗口：同一动作在此时间内只执行一次
// S8.4.3-d: 保持 500ms，用于防止同一事件源（如 visibilitychange+blur 同时触发 leave）重复执行
const DEDUP_WINDOW = 500;
// 事件列表最大长度
const MAX_EVENTS = 100;
// 网络事件最大长度
const MAX_NETWORK_EVENTS = 20;
// 屏幕事件最大长度
const MAX_ORIENTATION_EVENTS = 20;
// S8.4.4: sessionStorage 持久化前缀（生命周期绑定标签页，防止多考试标签污染）
const STORAGE_PREFIX = 'exam_monitor_';

// S8.4.6: 监考调试日志开关 —— 开发环境自动开启，生产环境关闭
// 覆盖方式：临时排查生产问题时可在控制台执行 localStorage.setItem('monitor_debug','1') 后刷新
const MONITOR_DEBUG = import.meta.env.DEV || (() => {
  try { return localStorage.getItem('monitor_debug') === '1'; } catch { return false; }
})();

/**
 * S8.4.6: 调试日志（仅 MONITOR_DEBUG 开启时输出）
 * 注意：console.warn / console.error 为关键错误日志，无条件保留，不经过此开关
 */
function mlog(...args) {
  if (MONITOR_DEBUG) console.log(...args);
}

// Element Plus 输入组件选择器（软键盘弹出触发 blur 的元素）
const INPUT_SELECTORS = 'input, textarea, [contenteditable="true"], .el-input__inner, .el-textarea__inner';

export function useMonitor() {
  // ============ 状态 ============
  const isMonitoring = ref(false);
  const isPageHidden = ref(false);
  const leaveCount = ref(0);
  const totalHiddenDuration = ref(0);
  const currentHiddenStart = ref(null);
  const events = ref([]);

  // S8.4.1: 环境采集数据（考试开始时采集一次）
  let environmentData = null;

  // S8.4.1: 横竖屏事件（独立存储，提交时合并到 events）
  const orientationEvents = ref([]);
  // S8.4.1: 网络状态事件（独立存储，提交时合并到 events）
  const networkEvents = ref([]);

  // 合并逻辑相关
  let pendingTimer = null;
  let pendingAction = null; // 'leave' | 'return' | null

  // 时间戳去重相关（S8.3.4.x BUG-001）
  let lastActionTime = 0;      // 上次实际执行动作的时间
  let lastActionType = null;   // 上次实际执行动作的类型

  // S8.4.4: sessionStorage 持久化（key 按考试记录隔离）
  let storageKey = null;       // 如 'exam_monitor_48'
  let storageAvailable = true; // 隐私模式等场景下 sessionStorage 不可用时退化为纯内存模式

  // 记录原始事件的处理函数引用（用于解绑）
  let handleVisibilityChange = null;
  let handleBlur = null;
  let handleFocus = null;
  let handlePageHide = null;   // S8.3.4.x BUG-003
  let handlePageShow = null;  // S8.3.4.x BUG-003

  // S8.4.1: 新增事件处理函数引用
  let handleOrientationChange = null;
  let handleOnline = null;
  let handleOffline = null;
  let handleResize = null;

  // ============ S8.4.1: 环境采集 ============

  /**
   * 采集考试环境信息
   * 在考试开始时调用一次，结果存入 environmentData
   */
  function collectEnvironment() {
    const ua = navigator.userAgent;
    const now = Date.now();

    // 检测浏览器类型
    let browser = 'unknown';
    if (/Chrome/i.test(ua)) browser = 'chrome';
    else if (/Safari/i.test(ua)) browser = 'safari';
    else if (/Firefox/i.test(ua)) browser = 'firefox';
    else if (/MicroMessenger/i.test(ua)) browser = 'wechat';
    else if (/Edg/i.test(ua)) browser = 'edge';

    // 检测操作系统
    let os = 'other';
    if (/Android/i.test(ua)) os = 'android';
    else if (/iPhone|iPad|iPod/i.test(ua)) os = 'ios';
    else if (/Windows/i.test(ua)) os = 'windows';
    else if (/Mac OS/i.test(ua)) os = 'macos';

    // 检测是否移动设备
    const isMobile = /iPhone|iPad|iPod|Android|Mobile/i.test(ua);

    // 获取屏幕方向
    let orientation = 'portrait';
    try {
      if (screen.orientation && screen.orientation.type) {
        orientation = screen.orientation.type.includes('landscape') ? 'landscape' : 'portrait';
      } else if (window.orientation !== undefined) {
        orientation = Math.abs(window.orientation) === 90 ? 'landscape' : 'portrait';
      } else {
        orientation = window.innerWidth > window.innerHeight ? 'landscape' : 'portrait';
      }
    } catch (e) {
      orientation = window.innerWidth > window.innerHeight ? 'landscape' : 'portrait';
    }

    // 网络类型（仅 Chrome 支持 effectiveType，其他浏览器降级处理）
    let effectiveType = '';
    try {
      if (navigator.connection && navigator.connection.effectiveType) {
        effectiveType = navigator.connection.effectiveType;
      }
    } catch (e) {
      // 忽略：某些浏览器不支持 Network Information API
    }

    environmentData = {
      device: {
        userAgent: ua.substring(0, 500), // 限制长度
        platform: os,
        language: navigator.language || navigator.userLanguage || '',
        isMobile,
        browser,
      },
      screen: {
        width: screen.width || 0,
        height: screen.height || 0,
        orientation,
        colorDepth: screen.colorDepth || 0,
      },
      network: {
        online: navigator.onLine,
        effectiveType,
      },
      browser: {
        viewportWidth: window.innerWidth || 0,
        viewportHeight: window.innerHeight || 0,
        pixelRatio: window.devicePixelRatio || 1,
      },
      collectedAt: now,
    };

    mlog('[Monitor] 环境信息已采集:', environmentData);
    return environmentData;
  }

  /**
   * 获取当前屏幕方向
   */
  function getCurrentOrientation() {
    try {
      if (screen.orientation && screen.orientation.type) {
        return screen.orientation.type.includes('landscape') ? 'landscape' : 'portrait';
      } else if (window.orientation !== undefined) {
        return Math.abs(window.orientation) === 90 ? 'landscape' : 'portrait';
      }
    } catch (e) {
      // 忽略
    }
    return window.innerWidth > window.innerHeight ? 'landscape' : 'portrait';
  }

  // ============ S8.4.4: sessionStorage 持久化 ============

  /**
   * 将监考状态同步写入 sessionStorage
   * 每次事件变化（leave/return/横竖屏/网络）后调用，确保页面被回收/刷新时数据不丢失
   */
  function persistData() {
    if (!storageKey || !storageAvailable) return;
    try {
      const payload = {
        version: 1,
        events: events.value,
        orientationEvents: orientationEvents.value,
        networkEvents: networkEvents.value,
        leaveCount: leaveCount.value,
        totalHiddenDuration: totalHiddenDuration.value,
        currentHiddenStart: currentHiddenStart.value,
        isPageHidden: isPageHidden.value,
        savedAt: Date.now(),
      };
      sessionStorage.setItem(storageKey, JSON.stringify(payload));
    } catch (e) {
      // 隐私模式 / 容量超限 / 序列化异常：退化为纯内存模式，不影响考试
      storageAvailable = false;
      console.warn('[Monitor] sessionStorage 写入失败，退化为内存模式:', e);
    }
  }

  /**
   * 恢复历史监考数据（页面刷新/浏览器回收后重新进入考试时调用）
   *
   * 异常恢复（场景1）：
   * 上次会话结束时页面处于 hidden（用户切出后浏览器被系统杀死），
   * 检测 lastHiddenTime 存在 → 以恢复时刻结算该次离开时长，
   * 生成 leave_recovered 事件，避免漏记。
   *
   * @returns {boolean} 是否成功恢复了历史数据
   */
  function restoreMonitorData() {
    if (!storageKey || !storageAvailable) return false;
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (!raw) return false;

      const history = JSON.parse(raw);
      // 基本结构校验，脏数据直接丢弃
      if (!history || typeof history !== 'object' || !Array.isArray(history.events)) {
        console.warn('[Monitor] 缓存数据结构异常，使用全新会话');
        return false;
      }

      events.value = history.events;
      orientationEvents.value = history.orientationEvents || [];
      networkEvents.value = history.networkEvents || [];
      leaveCount.value = history.leaveCount || 0;
      totalHiddenDuration.value = history.totalHiddenDuration || 0;

      // 新会话页面必然可见
      isPageHidden.value = false;

      // 场景1 补偿：上次会话在页面隐藏时被终止（浏览器被杀/回收）
      if (history.currentHiddenStart) {
        const lastHidden = history.currentHiddenStart;
        const now = Date.now();
        const duration = Math.max(0, now - lastHidden);

        leaveCount.value += 1;
        totalHiddenDuration.value += duration;

        // 补全最后一条 leave 事件的时长
        const lastEvent = events.value[events.value.length - 1];
        if (lastEvent && lastEvent.type === 'exam_leave') {
          lastEvent.endTime = now;
          lastEvent.duration = duration;
          lastEvent.tags = [...new Set([
            ...(lastEvent.tags || []),
            'recovered',
            ...(duration >= 60000 ? ['long_leave'] : []),
          ])];
        }

        // 生成恢复事件（区别于正常 return，供 HR 端识别异常终止）
        events.value.push({
          type: 'leave_recovered',
          timestamp: lastHidden,
          endTime: now,
          duration,
          tags: ['recovered', ...(duration >= 60000 ? ['long_leave'] : [])],
        });

        mlog(`[Monitor] 检测到上次会话在隐藏状态被终止，已补偿记录离开 ${duration}ms`);
      }

      currentHiddenStart.value = null;
      mlog(
        `[Monitor] 已恢复历史监考数据: leaveCount=${leaveCount.value}, ` +
        `duration=${totalHiddenDuration.value}ms, events=${events.value.length}条`
      );
      return true;
    } catch (e) {
      console.warn('[Monitor] 恢复监考数据失败，使用全新会话:', e);
      return false;
    }
  }

  /**
   * 提交成功后清除监考缓存（由 Exam.vue 在 submitExam 成功后调用）
   * 防止重进考试时重复累计历史数据；提交失败时保留缓存以便下次恢复
   */
  function clearPersistedData() {
    if (!storageKey) return;
    try {
      sessionStorage.removeItem(storageKey);
      mlog('[Monitor] 监考缓存已清除');
    } catch (e) {
      // 忽略清除失败
    }
  }

  // ============ 核心逻辑 ============

  /**
   * 判断是否为输入框聚焦导致的 blur/焦点事件（S8.3.4.x BUG-002）
   * 移动端软键盘弹出时会触发 blur，需排除此场景
   */
  function isInputElementFocused() {
    const activeEl = document.activeElement;
    if (!activeEl) return false;

    // 检查原生输入元素
    const tag = activeEl.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
    if (activeEl.isContentEditable) return true;

    // 检查 Element Plus 输入组件
    if (activeEl.closest('.el-input') || activeEl.closest('.el-textarea')) return true;
    if (activeEl.classList && activeEl.classList.contains('el-input__inner')) return true;
    if (activeEl.classList && activeEl.classList.contains('el-textarea__inner')) return true;

    return false;
  }

  /**
   * 合并事件处理（S8.4.3-d 重写）：
   * 解决移动端切屏检测失效的核心问题
   * 
   * 旧逻辑问题（已修复）：
   * - 300ms 合并窗口内 leave 被阻塞后，return 到来时被直接 return 丢弃
   * - 导致 isPageHidden 永远为 false，onPageLeave/onPageReturn 都无法正确记录
   * - DEDUP_WINDOW 逻辑过于宽泛，可能误杀合法事件
   * 
   * 新逻辑：
   * 1. 区分「同事件源重复」（应去重）和「状态切换」（必须响应）
   * 2. leave 和 return 是不同的 action 类型，永远不应该互相去重
   * 3. 同类型事件在短时间内（100ms）视为同一事件源的重复触发
   * 4. 使用 100ms 短窗口而非 300ms 合并，提高响应速度
   */
  function scheduleAction(action) {
    const now = Date.now();
    
    // 记录原始事件时间戳用于调试
    mlog(`[Monitor] scheduleAction('${action}') at ${new Date(now).toISOString()}, prevAction=${pendingAction}, lastExecuted=${lastActionType}(${lastActionTime ? Math.round((now - lastActionTime)/1000) + 's ago' : 'N/A'})`);

    // === 核心修复：同类型事件去重（仅针对完全相同的 action）===
    // 当 visibilitychange + blur + pagehide 同时触发 leave 时，
    // 它们都是 'leave' 类型，应该被合并为一次
    // 但 leave → return 是状态切换，绝对不能去重
    if (action === lastActionType && (now - lastActionTime) < DEDUP_WINDOW) {
      // 同一动作在极短时间内被同一事件源重复触发 → 忽略
      mlog(`[Monitor] 去重: ${action} 在 ${Math.round(now - lastActionTime)}ms 内重复触发`);
      return;
    }

    // === 核心修复：允许不同 action 抢占 pending ===
    // 当 leave 已在 pending 中等待时，若 return 到来：
    // - 旧逻辑：return 被丢弃（return 语句）→ 导致事件丢失
    // - 新逻辑：立即执行 pending 的 leave，然后将 return 设为新的 pending
    if (pendingAction && pendingTimer && pendingAction !== action) {
      // 不同的 action 类型到达 → 立即执行 pending 的旧 action，再安排新 action
      clearTimeout(pendingTimer);
      mlog(`[Monitor] 状态切换: 立即执行 pending 的 '${pendingAction}'，然后安排 '${action}'`);
      executeAction(pendingAction);
      pendingAction = null;
      pendingTimer = null;
      // 不 return，继续安排新的 action
    }

    // === 安排新 action ===
    // 同类型事件：取消旧定时器，重新计时（防抖合并）
    // 不同类型事件：已在上方处理，此处直接安排
    if (pendingAction === action && pendingTimer) {
      clearTimeout(pendingTimer);
    }

    pendingAction = action;
    clearTimeout(pendingTimer);
    pendingTimer = setTimeout(() => {
      const currentAction = pendingAction;
      executeAction(currentAction);
      pendingAction = null;
      pendingTimer = null;
    }, MERGE_WINDOW);
  }

  /**
   * 执行实际的状态变更
   */
  function executeAction(action) {
    // S8.3.4.x BUG-001: 记录执行时间戳和类型用于去重
    lastActionTime = Date.now();
    lastActionType = action;

    if (action === 'leave') {
      onPageLeave();
    } else if (action === 'return') {
      onPageReturn();
    }
  }

  /**
   * S8.4.2: 计算异常标签
   * @param {string} stage - 'leave' 或 'return'
   * @param {number} duration - 离开时长（毫秒，仅 return 阶段有）
   * @param {number} timestamp - 当前时间戳
   * @returns {string[]} 标签数组
   */
  function calculateTags(stage, duration, timestamp) {
    const tags = [];

    if (stage === 'leave') {
      // S8.4.2: 检测网络相关离开（30秒内有 offline 事件）
      const recentOffline = networkEvents.value.filter(
        (e) => e.type === 'network_offline' && (timestamp - e.timestamp) < 30000
      );
      if (recentOffline.length > 0) {
        tags.push('network_related');
      }

      // S8.4.2: 检测高频离开（5分钟内 leave 事件 >= 3 次）
      const fiveMinAgo = timestamp - 5 * 60 * 1000;
      const recentLeaves = events.value.filter(
        (e) => e.type === 'exam_leave' && e.timestamp >= fiveMinAgo
      );
      if (recentLeaves.length >= 2) { // >=2 because this leave hasn't been added yet
        tags.push('frequent_leave');
      }
    }

    if (stage === 'return') {
      // S8.4.2: 检测快速返回（<= 5秒）
      if (duration > 0 && duration <= 5000) {
        tags.push('rapid_leave_return');
      }

      // S8.4.2: 检测长时间离开（>= 60秒）
      if (duration >= 60000) {
        tags.push('long_leave');
      }
    }

    return tags;
  }

  /**
   * 页面离开处理
   */
  function onPageLeave() {
    if (!isMonitoring.value || isPageHidden.value) return;

    isPageHidden.value = true;
    currentHiddenStart.value = Date.now();

    // S8.4.2: 计算离开时的异常标签
    const tags = calculateTags('leave', 0, currentHiddenStart.value);

    // 记录事件
    const leaveEvent = {
      type: 'exam_leave',
      timestamp: currentHiddenStart.value,
      tags,
      // duration 将在返回时计算
    };
    events.value.push(leaveEvent);

    // S8.4.4: 同步持久化（页面此时被回收也能保住 leave 记录）
    persistData();

    if (tags.length > 0) {
      mlog(`[Monitor] 页面离开 [${tags.join(',')}]`, new Date().toISOString());
    } else {
      mlog('[Monitor] 页面离开', new Date().toISOString());
    }
  }

  /**
   * 页面返回处理
   */
  function onPageReturn() {
    if (!isMonitoring.value || !isPageHidden.value) return;

    const now = Date.now();
    const startTime = currentHiddenStart.value || now;
    const duration = now - startTime;

    isPageHidden.value = false;
    currentHiddenStart.value = null;

    // 更新统计
    leaveCount.value++;
    totalHiddenDuration.value += duration;

    // S8.4.2: 计算返回时的异常标签
    const tags = calculateTags('return', duration, now);

    // 更新最后一个事件的 duration、endTime 和 tags
    const lastEvent = events.value[events.value.length - 1];
    if (lastEvent && lastEvent.type === 'exam_leave') {
      lastEvent.endTime = now;
      lastEvent.duration = duration;
      // 合并标签（leave 阶段的 tag + return 阶段的 tag）
      lastEvent.tags = [...new Set([...(lastEvent.tags || []), ...tags])];
    }

    // 添加返回事件
    events.value.push({
      type: 'exam_return',
      timestamp: now,
      duration,
      tags,
    });

    const tagStr = tags.length > 0 ? ` [${tags.join(',')}]` : '';
    mlog(`[Monitor] 页面返回${tagStr}, 离开时长: ${duration}ms, 累计: ${totalHiddenDuration.value}ms, 次数: ${leaveCount.value}`);

    // S8.4.4: 同步持久化
    persistData();
  }

  // ============ 事件处理函数 ============

  /**
   * visibilitychange 事件处理
   * 主要事件源，在现代浏览器中工作良好
   * S8.4.3-d: 增强日志便于调试
   */
  function onVisibilityChange() {
    if (!isMonitoring.value) return;
    
    const state = document.visibilityState;
    mlog(`[Monitor] visibilitychange: state=${state}`);
    
    if (state === 'hidden') {
      scheduleAction('leave');
    } else {
      scheduleAction('return');
    }
  }

  /**
   * blur 事件处理（辅助事件源）
   * S8.4.3-d: 增强移动端兼容性
   * - 移动端切换到后台时 blur 可能先于 visibilitychange 触发
   * - 页面内 blur（如切换到其他标签页）也需捕获
   */
  function onWindowBlur() {
    if (!isMonitoring.value) return;
    
    // S8.3.4.x BUG-002: 输入框聚焦导致的 blur 不处理（软键盘弹出场景）
    if (isInputElementFocused()) {
      mlog('[Monitor] blur 被忽略: 输入框聚焦中');
      return;
    }
    
    // 如果 visibilitychange 已将页面标记为 hidden，则跳过
    // 但如果 visibilitychange 未触发（移动端常见），blur 作为独立检测
    if (document.visibilityState === 'hidden') {
      mlog('[Monitor] blur 已被 visibilitychange 处理，跳过');
      return;
    }
    
    mlog('[Monitor] blur 触发 leave（辅助检测）');
    scheduleAction('leave');
  }

  /**
   * focus 事件处理（辅助事件源）
   * S8.4.3-d: 增加对未完成 leave 的补偿
   * - 当 focus 先于 visibilitychange 触发时
   * - 检查是否有 pending 的 leave 未执行
   */
  function onWindowFocus() {
    if (!isMonitoring.value) return;
    
    mlog('[Monitor] focus 触发');
    
    // 如果页面当前标记为 hidden（说明 leave 已执行），直接安排 return
    if (isPageHidden.value) {
      mlog('[Monitor] focus: 页面已隐藏，安排 return');
      scheduleAction('return');
      return;
    }
    
    // 如果有 pending 的 leave（leave 已触发但还在等待合并窗口）
    // 这是移动端快速切屏返回的关键场景
    if (pendingAction === 'leave') {
      mlog('[Monitor] focus: leave 在 pending 中，立即执行 leave 再安排 return');
      // 立即执行 pending 的 leave
      if (pendingTimer) {
        clearTimeout(pendingTimer);
        pendingTimer = null;
      }
      executeAction('leave');
      pendingAction = null;
      // 然后安排 return
      scheduleAction('return');
      return;
    }
    
    // visibilitychange 已经处理（页面可见状态下）
    if (document.visibilityState === 'visible') {
      // 但如果 isPageHidden 仍为 false（leave 未执行），
      // 说明这是正常的焦点变化（如切回标签页但未离开），不做处理
      mlog('[Monitor] focus: 页面可见，无需处理');
      return;
    }
    
    // 其他情况：安排 return
    mlog('[Monitor] focus: 安排 return');
    scheduleAction('return');
  }

  /**
   * pagehide 事件处理
   * S8.4.3-d: 增加 force 参数支持
   * iOS Safari 后台切换时 visibilitychange 可能不触发
   * pagehide 作为独立事件源，不依赖 visibilityState
   */
  function onPageHide() {
    if (!isMonitoring.value) return;
    
    // 如果 visibilitychange 已经处理（页面已隐藏），跳过
    if (isPageHidden.value || document.visibilityState === 'hidden') {
      return;
    }
    
    mlog('[Monitor] pagehide 触发 leave');
    scheduleAction('leave');
  }

  /**
   * pageshow 事件处理
   * S8.4.3-d: 增加对 pending leave 的补偿
   * iOS Safari 页面恢复时 visibilitychange 可能不触发
   * pageshow 作为独立事件源
   * S8.4.1: 检测 bfcache（persisted），记录刷新/重新加载事件
   */
  function onPageShow(event) {
    if (!isMonitoring.value) return;
    
    // S8.4.1: 检测 bfcache 恢复
    if (event && event.persisted) {
      events.value.push({
        type: 'refresh_attempt',
        timestamp: Date.now(),
        source: 'bfcache_restore',
      });
      persistData(); // S8.4.4: 同步持久化
      mlog('[Monitor] 检测到页面从 bfcache 恢复（可能为刷新操作）');
    }
    
    // 如果页面已标记为 hidden（leave 已执行），直接安排 return
    if (isPageHidden.value) {
      mlog('[Monitor] pageshow: 页面已隐藏，安排 return');
      scheduleAction('return');
      return;
    }
    
    // 如果有 pending 的 leave，立即执行再安排 return
    if (pendingAction === 'leave') {
      mlog('[Monitor] pageshow: leave 在 pending 中，立即执行 leave 再安排 return');
      if (pendingTimer) {
        clearTimeout(pendingTimer);
        pendingTimer = null;
      }
      executeAction('leave');
      pendingAction = null;
      scheduleAction('return');
      return;
    }
    
    // 如果 visibilitychange 已处理，跳过
    if (document.visibilityState === 'visible' && !isPageHidden.value) {
      mlog('[Monitor] pageshow: 页面可见且未隐藏，跳过');
      return;
    }
    
    mlog('[Monitor] pageshow: 安排 return');
    scheduleAction('return');
  }

  // ============ S8.4.1: 新增事件处理 ============

  /**
   * 横竖屏切换事件处理
   */
  function onOrientationChange() {
    if (!isMonitoring.value) return;

    const newOrientation = getCurrentOrientation();
    const prevOrientation = orientationEvents.value.length > 0
      ? orientationEvents.value[orientationEvents.value.length - 1].to
      : (environmentData?.screen?.orientation || 'portrait');

    if (newOrientation !== prevOrientation) {
      const event = {
        type: 'orientation_change',
        from: prevOrientation,
        to: newOrientation,
        timestamp: Date.now(),
      };
      orientationEvents.value.push(event);

      // 限制数量
      if (orientationEvents.value.length > MAX_ORIENTATION_EVENTS) {
        orientationEvents.value = orientationEvents.value.slice(-MAX_ORIENTATION_EVENTS);
      }

      persistData(); // S8.4.4: 同步持久化
      mlog(`[Monitor] 屏幕方向变化: ${prevOrientation} → ${newOrientation}`);
    }
  }

  /**
   * 窗口尺寸变化处理（作为 orientationchange 的补充）
   * 使用 debounce 避免频繁触发
   */
  let resizeTimer = null;
  function onWindowResize() {
    if (!isMonitoring.value) return;

    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      // 检测是否为方向变化（宽高比互换）
      const w = window.innerWidth;
      const h = window.innerHeight;
      const newOrientation = w > h ? 'landscape' : 'portrait';

      const prevOrientation = orientationEvents.value.length > 0
        ? orientationEvents.value[orientationEvents.value.length - 1].to
        : (environmentData?.screen?.orientation || 'portrait');

      if (newOrientation !== prevOrientation) {
        const event = {
          type: 'orientation_change',
          from: prevOrientation,
          to: newOrientation,
          timestamp: Date.now(),
          source: 'resize',
        };
        orientationEvents.value.push(event);

        if (orientationEvents.value.length > MAX_ORIENTATION_EVENTS) {
          orientationEvents.value = orientationEvents.value.slice(-MAX_ORIENTATION_EVENTS);
        }

        persistData(); // S8.4.4: 同步持久化
        mlog(`[Monitor] 屏幕方向变化(resize): ${prevOrientation} → ${newOrientation}`);
      }
    }, 300);
  }

  /**
   * 网络上线事件
   */
  function onNetworkOnline() {
    if (!isMonitoring.value) return;

    const event = {
      type: 'network_online',
      timestamp: Date.now(),
    };
    networkEvents.value.push(event);

    if (networkEvents.value.length > MAX_NETWORK_EVENTS) {
      networkEvents.value = networkEvents.value.slice(-MAX_NETWORK_EVENTS);
    }

    persistData(); // S8.4.4: 同步持久化
    mlog('[Monitor] 网络恢复在线');
  }

  /**
   * 网络离线事件
   */
  function onNetworkOffline() {
    if (!isMonitoring.value) return;

    const event = {
      type: 'network_offline',
      timestamp: Date.now(),
    };
    networkEvents.value.push(event);

    if (networkEvents.value.length > MAX_NETWORK_EVENTS) {
      networkEvents.value = networkEvents.value.slice(-MAX_NETWORK_EVENTS);
    }

    persistData(); // S8.4.4: 同步持久化
    mlog('[Monitor] 网络断开离线');
  }

  // ============ 生命周期控制 ============

  /**
   * 启动监考
   * S8.4.4: 接受 recordId 参数用于 sessionStorage 隔离；
   *         页面刷新/浏览器回收后重新进入时，恢复历史监考数据而非清零
   * @param {number|string} recordId 考试记录ID（用于存储 key 隔离）
   */
  function startMonitoring(recordId = null) {
    if (isMonitoring.value) return;

    // S8.4.4: 初始化存储 key（按考试记录隔离）
    storageKey = recordId != null ? `${STORAGE_PREFIX}${recordId}` : null;

    // S8.4.4: 尝试恢复历史监考数据（刷新/浏览器回收场景）
    const restored = restoreMonitorData();

    if (!restored) {
      // 全新会话：重置状态
      isPageHidden.value = false;
      leaveCount.value = 0;
      totalHiddenDuration.value = 0;
      currentHiddenStart.value = null;
      events.value = [];
      orientationEvents.value = [];
      networkEvents.value = [];
    }
    environmentData = null;

    // S8.3.4.x BUG-001: 重置去重时间戳
    lastActionTime = 0;
    lastActionType = null;

    // S8.4.1: 采集考试环境信息（每次会话重新采集）
    collectEnvironment();

    // S8.4.4: 恢复补偿后立即持久化一次
    persistData();

    // 绑定事件
    handleVisibilityChange = onVisibilityChange;
    handleBlur = onWindowBlur;
    handleFocus = onWindowFocus;
    // S8.3.4.x BUG-003: 绑定 pagehide/pageshow
    handlePageHide = onPageHide;
    handlePageShow = onPageShow;

    // S8.4.1: 绑定新增事件
    handleOrientationChange = onOrientationChange;
    handleOnline = onNetworkOnline;
    handleOffline = onNetworkOffline;
    handleResize = onWindowResize;

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);
    // S8.3.4.x BUG-003: 绑定 pagehide/pageshow
    window.addEventListener('pagehide', handlePageHide);
    window.addEventListener('pageshow', handlePageShow);

    // S8.4.1: 绑定横竖屏检测（orientationchange + resize 双重保障）
    window.addEventListener('orientationchange', handleOrientationChange);
    window.addEventListener('resize', handleResize);

    // S8.4.1: 绑定网络状态检测
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    isMonitoring.value = true;
    mlog('[Monitor] 监考已启动');
  }

  /**
   * 停止监考
   */
  function stopMonitoring() {
    if (!isMonitoring.value) return;

    // 如果页面仍在后台，计算当前的离开时长
    if (isPageHidden.value) {
      const now = Date.now();
      const duration = now - currentHiddenStart.value;
      totalHiddenDuration.value += duration;

      const lastEvent = events.value[events.value.length - 1];
      if (lastEvent && lastEvent.type === 'exam_leave') {
        lastEvent.endTime = now;
        lastEvent.duration = duration;
      }

      leaveCount.value++;
      currentHiddenStart.value = null;
      isPageHidden.value = false;
    }

    // 解绑事件
    if (handleVisibilityChange) {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      handleVisibilityChange = null;
    }
    if (handleBlur) {
      window.removeEventListener('blur', handleBlur);
      handleBlur = null;
    }
    if (handleFocus) {
      window.removeEventListener('focus', handleFocus);
      handleFocus = null;
    }
    // S8.3.4.x BUG-003: 解绑 pagehide/pageshow
    if (handlePageHide) {
      window.removeEventListener('pagehide', handlePageHide);
      handlePageHide = null;
    }
    if (handlePageShow) {
      window.removeEventListener('pageshow', handlePageShow);
      handlePageShow = null;
    }

    // S8.4.1: 解绑新增事件
    if (handleOrientationChange) {
      window.removeEventListener('orientationchange', handleOrientationChange);
      handleOrientationChange = null;
    }
    if (handleResize) {
      window.removeEventListener('resize', handleResize);
      handleResize = null;
    }
    if (handleOnline) {
      window.removeEventListener('online', handleOnline);
      handleOnline = null;
    }
    if (handleOffline) {
      window.removeEventListener('offline', handleOffline);
      handleOffline = null;
    }

    // 清理 resize debounce 定时器
    if (resizeTimer) {
      clearTimeout(resizeTimer);
      resizeTimer = null;
    }

    // 清理待处理的合并动作
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
    pendingAction = null;

    isMonitoring.value = false;
    // S8.4.4: 停止时持久化当前状态（未提交就离开时，下次进入可恢复）
    persistData();
    mlog('[Monitor] 监考已停止');
  }

  /**
   * 刷新并获取监考数据
   * S8.4.3-d: 增强处理边缘情况
   * - 确保 pending 的 leave/return 事件被正确处理
   * - 处理 isPageHidden 为 false 但有未完成 leave 的边缘情况
   * - 增加完整的调试日志
   * @returns {Object} 监考汇总数据
   */
  function flushEvents() {
    mlog(`[Monitor] flushEvents 开始: isPageHidden=${isPageHidden.value}, leaveCount=${leaveCount.value}, pendingAction=${pendingAction}`);
    
    // 1. 先处理待处理的事件（pending 中的 leave/return）
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
      if (pendingAction) {
        mlog(`[Monitor] flushEvents: 执行 pending 的 '${pendingAction}'`);
        executeAction(pendingAction);
        pendingAction = null;
      }
    }

    // 2. 如果页面仍在后台，计算时长
    if (isPageHidden.value) {
      const now = Date.now();
      const duration = now - currentHiddenStart.value;
      totalHiddenDuration.value += duration;
      leaveCount.value++;

      const lastEvent = events.value[events.value.length - 1];
      if (lastEvent && lastEvent.type === 'exam_leave') {
        lastEvent.endTime = now;
        lastEvent.duration = duration;
      }
      mlog(`[Monitor] flushEvents: 页面仍在后台，补充时长 ${duration}ms`);
    } else if (currentHiddenStart.value !== null) {
      // 边缘情况：isPageHidden 为 false 但 currentHiddenStart 不为 null
      // 说明 leave 已执行但 return 未执行（如移动端后台未触发 return）
      mlog('[Monitor] flushEvents: 异常状态检测 - isPageHidden=false 但 currentHiddenStart 不为 null');
      const now = Date.now();
      const duration = now - currentHiddenStart.value;
      if (duration > 0) {
        totalHiddenDuration.value += duration;
        leaveCount.value++;
        
        const lastEvent = events.value[events.value.length - 1];
        if (lastEvent && lastEvent.type === 'exam_leave') {
          lastEvent.endTime = now;
          lastEvent.duration = duration;
        }
        mlog(`[Monitor] flushEvents: 补偿计算时长 ${duration}ms`);
      }
      currentHiddenStart.value = null;
    }

    // 3. 合并所有事件到统一列表
    const allEvents = [
      ...events.value,
      ...orientationEvents.value,
      ...networkEvents.value,
    ];

    // 按时间戳排序
    allEvents.sort((a, b) => a.timestamp - b.timestamp);

    // 限制总事件数量
    const limitedEvents = allEvents.slice(-MAX_EVENTS);

    const data = {
      leave_count: leaveCount.value,
      total_hidden_duration: totalHiddenDuration.value,
      events: limitedEvents,
      environment: environmentData,
    };

    mlog(`[Monitor] flushEvents 完成: leaveCount=${data.leave_count}, duration=${data.total_hidden_duration}ms, events=${data.events.length}条`);

    // S8.4.4: 导出后同步持久化（补偿计算的结果也写入缓存；
    // 提交成功后由 Exam.vue 调用 clearPersistedData 清除，失败则保留供下次恢复）
    persistData();
    return data;
  }

  // 组件卸载时自动清理
  onBeforeUnmount(() => {
    stopMonitoring();
  });

  // ============ 返回值 ============
  return {
    // 状态
    isMonitoring,
    isPageHidden,
    leaveCount,
    totalHiddenDuration,
    currentHiddenStart,
    events,

    // S8.4.1: 新增状态暴露（供调试使用）
    orientationEvents,
    networkEvents,
    environmentData: () => environmentData,

    // 控制函数
    startMonitoring,
    stopMonitoring,
    flushEvents,

    // S8.4.4: 持久化控制（提交成功后由页面调用清除）
    clearPersistedData,

    // S8.4.1: 新增暴露
    collectEnvironment,
  };
}
