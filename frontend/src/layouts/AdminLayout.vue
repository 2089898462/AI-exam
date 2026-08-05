<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <div class="logo">
        <el-icon :size="24" color="#409eff"><Reading /></el-icon>
        <span class="logo-text">考试系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="#b7bdc6"
        active-text-color="#ffffff"
        unique-opened
      >
        <el-sub-menu index="exam">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>考试管理</span>
          </template>
          <el-menu-item index="/admin/exams">考试列表</el-menu-item>
          <el-menu-item index="/admin/exams/create">创建考试</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin/exams' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title && $route.name !== 'ExamList'">
              {{ $route.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" style="background-color: #409eff">
                <User />
              </el-avatar>
              <span class="username">{{ userStore.displayName || '用户' }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Reading, Document, User } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const activeMenu = computed(() => route.path)

async function handleCommand(command) {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
      userStore.logout()
      ElMessage.success('已退出登录')
      router.push('/login')
    } catch {
      // User cancelled
    }
  }
}
</script>

<style scoped>
.admin-layout {
  height: 100vh;
}

.admin-aside {
  background-color: #001529;
  overflow-y: auto;
  transition: width 0.28s;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 60px;
  background-color: #002140;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  gap: 8px;
}

.logo-text {
  white-space: nowrap;
}

.admin-aside .el-menu {
  border-right: none;
}

.admin-aside .el-menu-item,
.admin-aside .el-sub-menu__title {
  height: 50px;
  line-height: 50px;
}

.admin-aside .el-menu-item.is-active {
  background-color: #409eff !important;
}

.admin-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e8eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  font-size: 14px;
  color: #303133;
}

.admin-main {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>