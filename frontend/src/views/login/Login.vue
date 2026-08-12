<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">企业AI智能考试系统</div>
        <div class="card-subtitle">HR 后台登录</div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="UserIcon" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password :prefix-icon="LockIcon" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const UserIcon = markRaw(User)
const LockIcon = markRaw(Lock)

const formRef = ref(null)
const loading = ref(false)
const router = useRouter()
const userStore = useUserStore()

const form = ref({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  console.log('[Login] 按钮点击触发')
  try {
    const valid = await formRef.value.validate().catch((err) => {
      console.log('[Login] 表单验证失败:', err)
      return false
    })
    console.log('[Login] 表单验证结果:', valid)
    if (!valid) return
    loading.value = true
    console.log('[Login] 开始登录, 用户名:', form.value.username)
    try {
      const res = await userStore.login(form.value)
      console.log('[Login] 登录成功:', res)
      ElMessage.success('登录成功')
      await new Promise(resolve => setTimeout(resolve, 100))
      router.replace('/admin/exams')
    } catch (e) {
      console.error('[Login] 登录失败:', e)
      // Error message already handled by request interceptor
    } finally {
      loading.value = false
    }
  } catch (err) {
    console.error('[Login] 异常:', err)
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 420px;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.card-header {
  text-align: center;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.card-subtitle {
  text-align: center;
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}
</style>
