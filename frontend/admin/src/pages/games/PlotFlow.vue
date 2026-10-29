<template>
  <div class="flow">
    <div class="flow-help">
      <span>{{ t('拖动卡片摆位置，滚动查看整张图。从圆点拖到另一段，就会接上跳转。有选项时，拖对应选项的圆点。') }}</span>
      <div class="flow-zoom">
        <ElButton size="small" @click="zoomBy(0.1)">{{ t('放大') }}</ElButton>
        <ElButton size="small" @click="zoomBy(-0.1)">{{ t('缩小') }}</ElButton>
        <ElButton size="small" @click="fit">{{ t('适应') }}</ElButton>
      </div>
    </div>
    <div v-if="armed" class="flow-arm">{{ t('正在为选项「{text}」选择跳转，点一段剧情。', { text: armed.text }) }}</div>
    <div v-loading="loading" class="flow-stage">
      <div ref="viewportRef" class="flow-view" @pointerdown="onBackgroundDown">
        <div v-if="loading" class="flow-empty">{{ t('正在加载流程图') }}</div>
        <div v-else-if="!nodes.length" class="flow-empty">{{ t('还没有剧情。先点右上角的「新剧情」。') }}</div>
        <div v-else class="flow-scaler" :style="scalerStyle">
          <div class="flow-world" :style="worldStyle">
          <svg class="flow-edges" :width="world.w" :height="world.h">
            <defs>
              <marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6 Z" fill="#8c8c8c" />
              </marker>
              <marker id="flow-arrow-choice" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6 Z" fill="#1677ff" />
              </marker>
            </defs>
            <path
              v-for="edge in edges"
              :key="`${edge.id}-hit`"
              :d="edge.path"
              class="flow-edge-hit"
              @pointerdown.stop="selectedEdgeId = edge.id; selectedId = null"
            />
            <path
              v-for="edge in edges"
              :key="edge.id"
              :d="edge.path"
              class="flow-edge"
              :class="{ choice: edge.kind === 'choice', on: selectedEdgeId === edge.id }"
              :marker-end="edge.kind === 'choice' ? 'url(#flow-arrow-choice)' : 'url(#flow-arrow)'"
            />
            <text v-for="edge in edges" :key="`${edge.id}-label`" class="flow-label" :x="edge.labelX" :y="edge.labelY">
              {{ edge.label }}
            </text>
            <path v-if="draftPath" :d="draftPath" class="flow-edge draft" />
          </svg>
          <div
            v-for="card in cards"
            :key="card.node.id"
            class="flow-node"
            :class="{
              on: selectedId === card.node.id,
              start: card.node.is_start,
              ending: card.node.is_ending,
              key: card.node.is_key,
            }"
            :style="{ left: `${card.x}px`, top: `${card.y}px` }"
            :data-node-id="card.node.id"
            @pointerdown.stop="onNodeDown($event, card.node.id)"
            @dblclick.stop="openNode(card.node.id)"
          >
            <div class="flow-node__key">{{ card.node.node_key }}</div>
            <div class="flow-node__speaker">{{ speakerOf(card.node) }}</div>
            <div class="flow-node__line">{{ excerpt(card.node.content) }}</div>
            <div class="flow-node__tags">
              <span v-if="card.node.is_start">{{ t('开场') }}</span>
              <span v-if="card.node.is_key">{{ t('关键') }}</span>
              <span v-if="card.node.is_ending">{{ t('结局') }}</span>
            </div>
            <template v-if="card.choices.length">
              <button
                v-for="(choice, index) in card.choices"
                :key="choice.id"
                type="button"
                class="port choice"
                :style="{ left: `${portLeft(index, card.choices.length)}px` }"
                :title="choice.text"
                @pointerdown.stop="onPortDown($event, card.node.id, 'choice', choice.id)"
              />
            </template>
            <button
              v-else
              type="button"
              class="port"
              :title="t('拖到下一段')"
              @pointerdown.stop="onPortDown($event, card.node.id, 'next')"
            />
          </div>
          </div>
        </div>
      </div>
      <aside v-if="selected" class="flow-side">
        <div class="flow-side__title">{{ selected.node_key }}</div>
        <p class="flow-side__line">{{ speakerOf(selected) }}：{{ excerpt(selected.content, 48) }}</p>
        <template v-if="selected.choices.length">
          <div v-for="choice in selected.choices" :key="choice.id" class="flow-choice">
            <div class="flow-choice__text">{{ choice.text }}</div>
            <ElSelect
              :model-value="choice.next_node"
              filterable
              :placeholder="t('跳转到')"
              @change="(value: number) => linkChoice(choice.id, value)"
            >
              <ElOption v-for="item in linkOptions(selected.id)" :key="item.id" :label="item.label" :value="item.id" />
            </ElSelect>
            <ElButton link type="danger" @click="removeChoice(choice.id, choice.text)">{{ t('去掉这个选项') }}</ElButton>
          </div>
        </template>
        <ElFormItem v-else :label="t('下一句')">
          <ElSelect
            :model-value="selected.next_node"
            clearable
            filterable
            :placeholder="t('不接下一句')"
            @change="(value: number | null) => { if (selected) linkNext(selected.id, value) }"
          >
            <ElOption v-for="item in linkOptions(selected.id)" :key="item.id" :label="item.label" :value="item.id" />
          </ElSelect>
        </ElFormItem>
        <div class="flow-side__actions">
          <ElButton size="small" @click="addChoice(selected.id)">{{ t('添加选项') }}</ElButton>
          <ElButton size="small" @click="copyNode(selected.id)">{{ t('基于此新建') }}</ElButton>
          <ElButton size="small" type="primary" @click="openNode(selected.id)">{{ t('编辑这段') }}</ElButton>
        </div>
      </aside>
      <aside v-else-if="selectedEdge" class="flow-side">
        <div class="flow-side__title">{{ selectedEdge.kind === 'choice' ? t('选项') : t('下一句') }}</div>
        <p class="flow-side__line">{{ selectedEdge.label }}</p>
        <ElButton type="danger" plain @click="disconnectEdge(selectedEdge)">{{ t('断开这条线') }}</ElButton>
      </aside>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { t } from '../../i18n'
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { request, type StoryNode } from '../../services/otome/api'
import { confirmDelete, notify } from '../../utils/feedback'

const NODE_W = 220
const NODE_H = 136
const COL = 300
const ROW = 184

const props = defineProps<{
  gameId: string
  nodes: StoryNode[]
  speakerOf: (node: StoryNode) => string
  loading?: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const router = useRouter()
const viewportRef = ref<HTMLElement | null>(null)
const positions = reactive<Record<number, { x: number; y: number }>>({})
const zoom = ref(1)
const selectedId = ref<number | null>(null)
const selectedEdgeId = ref<string | null>(null)
const armed = ref<{ fromId: number; text: string } | null>(null)
const draft = ref<{ fromId: number; kind: 'next' | 'choice'; choiceId?: number; x: number; y: number } | null>(null)
const saving = ref(false)

let gesture: { id: number; dx: number; dy: number } | null = null

const selected = computed(() => props.nodes.find((item) => item.id === selectedId.value) || null)

function choicesOf(node: StoryNode) {
  return node.choices || []
}

function excerpt(text: string, size = 32) {
  const line = (text || '').replace(/\s+/g, ' ').trim()
  return line.length > size ? `${line.slice(0, size)}…` : line
}

function nodeTitle(node: StoryNode) {
  const line = excerpt(node.content, 18)
  const speaker = props.speakerOf(node)
  return line ? `${speaker}：${line}` : speaker
}

function linkOptions(selfId: number) {
  return props.nodes
    .filter((item) => item.id !== selfId)
    .map((item) => ({ id: item.id, label: nodeTitle(item) }))
}

function portLeft(index: number, count: number) {
  return ((index + 1) * NODE_W) / (count + 1) - 7
}

function portPoint(nodeId: number, kind: 'next' | 'choice', choiceId?: number) {
  const pos = positions[nodeId] || { x: 0, y: 0 }
  const node = props.nodes.find((item) => item.id === nodeId)
  const choices = node ? choicesOf(node) : []
  if (kind === 'choice' && choiceId) {
    const index = Math.max(0, choices.findIndex((item) => item.id === choiceId))
    return { x: pos.x + portLeft(index, choices.length) + 7, y: pos.y + NODE_H }
  }
  return { x: pos.x + NODE_W / 2, y: pos.y + NODE_H }
}

function curve(from: { x: number; y: number }, to: { x: number; y: number }) {
  const bend = Math.max(36, Math.min(90, Math.abs(to.y - from.y) * 0.45))
  return `M ${from.x} ${from.y} C ${from.x} ${from.y + bend}, ${to.x} ${to.y - bend}, ${to.x} ${to.y}`
}

const cards = computed(() =>
  props.nodes.map((node) => ({
    node,
    choices: choicesOf(node),
    x: positions[node.id]?.x || 0,
    y: positions[node.id]?.y || 0,
  })),
)

const edges = computed(() => {
  const found: {
    id: string
    kind: 'next' | 'choice'
    fromId: number
    toId: number
    choiceId?: number
    label: string
    path: string
    labelX: number
    labelY: number
  }[] = []
  props.nodes.forEach((node) => {
    const choices = choicesOf(node)
    const links = choices.length
      ? choices.map((choice) => ({
          id: `choice-${choice.id}`,
          kind: 'choice' as const,
          toId: choice.next_node,
          choiceId: choice.id,
          label: excerpt(choice.text, 10),
        }))
      : node.next_node
        ? [{ id: `next-${node.id}`, kind: 'next' as const, toId: node.next_node, label: t('下一句') }]
        : []
    links.forEach((link) => {
      if (!positions[node.id] || !positions[link.toId]) return
      const from = portPoint(node.id, link.kind, 'choiceId' in link ? link.choiceId : undefined)
      const to = { x: positions[link.toId].x + NODE_W / 2, y: positions[link.toId].y }
      found.push({
        ...link,
        fromId: node.id,
        path: curve(from, to),
        labelX: from.x + (to.x - from.x) * 0.42,
        labelY: from.y + (to.y - from.y) * 0.42 - 8,
      })
    })
  })
  return found
})

const selectedEdge = computed(() => edges.value.find((item) => item.id === selectedEdgeId.value) || null)

const world = computed(() => {
  const xs = Object.values(positions)
  const width = xs.reduce((max, item) => Math.max(max, item.x), 0) + NODE_W + 80
  const height = xs.reduce((max, item) => Math.max(max, item.y), 0) + NODE_H + 80
  return { w: Math.max(width, 640), h: Math.max(height, 420) }
})

const worldStyle = computed(() => ({
  width: `${world.value.w}px`,
  height: `${world.value.h}px`,
  transform: `scale(${zoom.value})`,
}))

const scalerStyle = computed(() => ({
  width: `${world.value.w * zoom.value}px`,
  height: `${world.value.h * zoom.value}px`,
}))

const draftPath = computed(() => {
  if (!draft.value) return ''
  return curve(portPoint(draft.value.fromId, draft.value.kind, draft.value.choiceId), draft.value)
})

function layoutNodes(list: StoryNode[]) {
  const depth = new Map<number, number>()
  const start = list.find((item) => item.is_start) || [...list].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)[0]
  if (start) {
    const queue = [start.id]
    depth.set(start.id, 0)
    while (queue.length) {
      const current = queue.shift() as number
      const node = list.find((item) => item.id === current)
      if (!node) continue
      const nextIds = choicesOf(node).length
        ? choicesOf(node).map((item) => item.next_node)
        : node.next_node
          ? [node.next_node]
          : []
      nextIds.forEach((nextId) => {
        if (!nextId || depth.has(nextId)) return
        depth.set(nextId, (depth.get(current) || 0) + 1)
        queue.push(nextId)
      })
    }
  }
  const columns = new Map<number, StoryNode[]>()
  list.forEach((node) => {
    if (!depth.has(node.id)) return
    const column = depth.get(node.id) || 0
    const bucket = columns.get(column) || []
    bucket.push(node)
    columns.set(column, bucket)
  })
  columns.forEach((bucket) => bucket.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id))
  columns.forEach((bucket, column) => {
    bucket.forEach((node, index) => {
      if (!positions[node.id]) positions[node.id] = { x: 40 + column * COL, y: 32 + index * ROW }
    })
  })
  const orphans = list.filter((node) => !positions[node.id]).sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
  const usedColumns = columns.size
  orphans.forEach((node, index) => {
    positions[node.id] = { x: 40 + usedColumns * COL, y: 32 + index * ROW }
  })
}

function syncPositions() {
  layoutNodes(props.nodes)
  Object.keys(positions).forEach((key) => {
    const id = Number(key)
    if (!props.nodes.some((item) => item.id === id)) delete positions[id]
  })
  if (selectedId.value && !props.nodes.some((item) => item.id === selectedId.value)) selectedId.value = null
}

function worldPoint(event: PointerEvent) {
  const view = viewportRef.value
  const rect = view?.getBoundingClientRect()
  return {
    x: (event.clientX - (rect?.left || 0) + (view?.scrollLeft || 0)) / zoom.value,
    y: (event.clientY - (rect?.top || 0) + (view?.scrollTop || 0)) / zoom.value,
  }
}

function zoomBy(delta: number) {
  zoom.value = Math.min(1.6, Math.max(0.4, Number((zoom.value + delta).toFixed(2))))
}

function fit() {
  const view = viewportRef.value
  if (!view || !props.nodes.length) return
  const pad = 32
  const scale = Math.min(
    (view.clientWidth - pad) / world.value.w,
    (view.clientHeight - pad) / world.value.h,
    1,
  )
  zoom.value = Math.max(0.45, Number(scale.toFixed(2)))
  nextTick(() => {
    if (!viewportRef.value) return
    viewportRef.value.scrollLeft = 0
    viewportRef.value.scrollTop = 0
  })
}

function listen(move: (event: PointerEvent) => void, up: (event: PointerEvent) => void) {
  const stop = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', (event) => {
    stop()
    up(event)
  })
}

function onBackgroundDown(event: PointerEvent) {
  const target = event.target as HTMLElement
  if (target.closest('.flow-node') || target.closest('.flow-edge') || target.closest('.flow-edge-hit')) return
  selectedId.value = null
  selectedEdgeId.value = null
}

function onNodeDown(event: PointerEvent, id: number) {
  if ((event.target as HTMLElement).closest('.port')) return
  if (armed.value && armed.value.fromId !== id) {
    const pending = armed.value
    armed.value = null
    void createChoice(pending.fromId, id, pending.text)
    return
  }
  selectedId.value = id
  selectedEdgeId.value = null
  const point = worldPoint(event)
  const pos = positions[id] || { x: 0, y: 0 }
  gesture = { id, dx: point.x - pos.x, dy: point.y - pos.y }
  listen(
    (moveEvent) => {
      if (!gesture) return
      const next = worldPoint(moveEvent)
      positions[gesture.id] = { x: next.x - gesture.dx, y: next.y - gesture.dy }
    },
    () => {
      gesture = null
    },
  )
}

function onPortDown(event: PointerEvent, fromId: number, kind: 'next' | 'choice', choiceId?: number) {
  const point = worldPoint(event)
  draft.value = { fromId, kind, choiceId, x: point.x, y: point.y }
  listen(
    (moveEvent) => {
      if (!draft.value) return
      const next = worldPoint(moveEvent)
      draft.value = { ...draft.value, x: next.x, y: next.y }
    },
    (upEvent) => {
      const link = draft.value
      draft.value = null
      if (!link) return
      const hit = document.elementFromPoint(upEvent.clientX, upEvent.clientY)?.closest('[data-node-id]')
      const targetId = Number(hit?.getAttribute('data-node-id') || 0)
      if (!targetId) return
      if (link.kind === 'choice' && link.choiceId) void linkChoice(link.choiceId, targetId)
      else void linkNext(link.fromId, targetId)
    },
  )
}

async function linkNext(fromId: number, targetId: number | null) {
  if (saving.value) return
  if (targetId === fromId) {
    notify(t('不能跳到自己'), 'warning')
    return
  }
  const source = props.nodes.find((item) => item.id === fromId)
  if (source && choicesOf(source).length) {
    notify(t('这段有选项，请改选项的跳转'), 'warning')
    return
  }
  saving.value = true
  try {
    await request(`/nodes/${fromId}/`, { method: 'PATCH', body: JSON.stringify({ next_node: targetId }) })
    notify(targetId ? t('下一句已接上') : t('已断开下一句'))
    emit('changed')
  } catch (err) {
    notify(err instanceof Error ? err.message : t('保存跳转失败'), 'error')
  } finally {
    saving.value = false
  }
}

async function linkChoice(choiceId: number, targetId: number) {
  if (saving.value) return
  const owner = props.nodes.find((item) => choicesOf(item).some((choice) => choice.id === choiceId))
  if (owner && targetId === owner.id) {
    notify(t('不能跳到自己'), 'warning')
    return
  }
  saving.value = true
  try {
    await request(`/choices/${choiceId}/`, { method: 'PATCH', body: JSON.stringify({ next_node: targetId }) })
    notify(t('选项跳转已更新'))
    emit('changed')
  } catch (err) {
    notify(err instanceof Error ? err.message : t('保存选项失败'), 'error')
  } finally {
    saving.value = false
  }
}

async function createChoice(fromId: number, targetId: number, text: string) {
  if (targetId === fromId) {
    notify(t('不能跳到自己'), 'warning')
    return
  }
  const source = props.nodes.find((item) => item.id === fromId)
  saving.value = true
  try {
    await request('/choices/', {
      method: 'POST',
      body: JSON.stringify({
        node: fromId,
        text,
        next_node: targetId,
        interact: null,
        sort_order: source ? choicesOf(source).length : 0,
      }),
    })
    notify(t('选项已接上'))
    selectedId.value = fromId
    emit('changed')
  } catch (err) {
    notify(err instanceof Error ? err.message : t('添加选项失败'), 'error')
  } finally {
    saving.value = false
  }
}

async function addChoice(fromId: number) {
  try {
    const { value } = await ElMessageBox.prompt(t('玩家会看到这段文字'), t('添加选项'), {
      confirmButtonText: t('去选跳转'),
      cancelButtonText: t('取消'),
      inputPlaceholder: t('例如：去天文台'),
    })
    const text = String(value || '').trim()
    if (!text) {
      notify(t('请填写选项文字'), 'warning')
      return
    }
    armed.value = { fromId, text }
  } catch {
    armed.value = null
  }
}

async function removeChoice(choiceId: number, text: string) {
  const agreed = await confirmDelete(t('去掉选项「{text}」？', { text }), t('去掉选项'))
  if (!agreed) return
  try {
    await request(`/choices/${choiceId}/`, { method: 'DELETE' })
    notify(t('选项已去掉'))
    emit('changed')
  } catch (err) {
    notify(err instanceof Error ? err.message : t('去掉选项失败'), 'error')
  }
}

async function disconnectEdge(edge: { kind: 'next' | 'choice'; fromId: number; choiceId?: number; label: string }) {
  if (edge.kind === 'choice' && edge.choiceId) {
    await removeChoice(edge.choiceId, edge.label)
    selectedEdgeId.value = null
    return
  }
  await linkNext(edge.fromId, null)
  selectedEdgeId.value = null
}

function openNode(id: number) {
  router.push({ name: 'node', params: { gameId: props.gameId, nodeId: id } })
}

function copyNode(id: number) {
  router.push({ name: 'node', params: { gameId: props.gameId, nodeId: 'new' }, query: { copy: String(id) } })
}

watch(
  () => props.nodes.map((item) => `${item.id}:${item.next_node}:${choicesOf(item).map((choice) => choice.id).join(',')}`).join('|'),
  () => {
    syncPositions()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  gesture = null
  draft.value = null
})
</script>

<style lang="scss" scoped>
.flow-help,
.flow-zoom,
.flow-side__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.flow-help {
  justify-content: space-between;
  margin-bottom: 8px;
  color: #909399;
  font-size: 13px;
}

.flow-arm {
  margin-bottom: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #e6f4ff;
  color: #0958d9;
}

.flow-stage {
  display: flex;
  height: 640px;
  overflow: hidden;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  background: #f7f8fa;
}

.flow-view {
  position: relative;
  flex: 1;
  overflow: auto;
  cursor: default;
}

.flow-empty {
  padding: 48px 24px;
  color: #909399;
}

.flow-scaler {
  position: relative;
}

.flow-world {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  background-image: radial-gradient(#d9d9d9 1px, transparent 1px);
  background-size: 22px 22px;
}

.flow-edges {
  position: absolute;
  top: 0;
  left: 0;
  overflow: visible;
}

.flow-edge,
.flow-edge-hit {
  fill: none;
  cursor: pointer;
}

.flow-edge {
  stroke: #8c8c8c;
  stroke-width: 2;
}

.flow-edge-hit {
  stroke: transparent;
  stroke-width: 16;
}

.flow-edge.choice {
  stroke: #1677ff;
}

.flow-edge.on,
.flow-edge.draft {
  stroke: #fa8c16;
  stroke-width: 3;
}

.flow-label {
  fill: #595959;
  font-size: 12px;
  text-anchor: middle;
  paint-order: stroke;
  stroke: #f7f8fa;
  stroke-width: 4px;
  pointer-events: none;
}

.flow-node {
  position: absolute;
  box-sizing: border-box;
  width: 220px;
  height: 136px;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  cursor: move;
  z-index: 1;
}

.flow-node.on {
  z-index: 2;
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.15);
}

.flow-node.ending {
  border-top: 3px solid #52c41a;
}

.flow-node.key {
  border-top: 3px solid #fa8c16;
}

.flow-node.start {
  border-top: 3px solid #1677ff;
}

.flow-node__key,
.flow-node__speaker {
  overflow: hidden;
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.flow-node__key {
  color: #909399;
}

.flow-node__speaker {
  margin-top: 4px;
  font-weight: 600;
}

.flow-node__line {
  display: -webkit-box;
  margin-top: 4px;
  overflow: hidden;
  color: #606266;
  font-size: 13px;
  line-height: 1.4;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.flow-node__tags {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  color: #1677ff;
  font-size: 12px;
}

.port {
  position: absolute;
  bottom: -7px;
  left: 103px;
  width: 14px;
  height: 14px;
  padding: 0;
  border: 2px solid #1677ff;
  border-radius: 50%;
  background: #fff;
  cursor: crosshair;
}

.flow-side {
  width: 280px;
  padding: 14px;
  overflow: auto;
  border-left: 1px solid #e5e6eb;
  background: #fff;
}

.flow-side__title {
  font-weight: 600;
}

.flow-side__line {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.flow-choice {
  margin-bottom: 12px;
}

.flow-choice__text {
  margin-bottom: 6px;
  font-size: 13px;
}

.flow-side__actions {
  margin-top: 12px;
}
</style>
