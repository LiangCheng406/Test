/**
 * 1. 同步账号，将页面所有子账号表格数据存浏览器存储并发送给后台。
 * 2. 开始任务，获取任务数据，跳转到子账号页面，点击内容管理，点击上传，填充cache缓存数据，选择话题，选择poi地址，选择封面图，选择发布时间，点击发布
 * 3. 停止任务，重置任务状态，并reload页面
 * 4. 保持登陆，重新加载table，切换page保持页面在操作
 * 5. 退出代运营状态，点击退出代运营状态
 */

// 接收来自popup的消息
//这个方法用于注册一个事件监听器，当扩展的其他部分（如 popup 或 content script）发送消息时，该监听器会被触发。
chrome.runtime.onMessage.addListener(async function (request, sender, sendResponse) {
  for (const key in request) {//遍历 request 对象中的每一个属性。
    if (request.hasOwnProperty(key)) {//确保 request 对象具有该属性（不是从原型链继承的属性）。
      const element = request[key]//获取属性值。
      localStorage.setItem(key, element)// 将每个属性值存储到浏览器的 localStorage 中，键是属性名，值是属性值。
    }
  }
  sendResponse('我收到你的消息了：' + JSON.stringify(request))//发送一个响应回到消息的发送者。
  var action = request['action']

  createNotification('操作：action----' + action)

  switch (action) {
    case 'sync': // 同步账号
      createNotification('准备开始同步账号')
      getAllAccount()
      break
    case 'start': // 开始任务
      localStorage.setItem('taskStatus', '1')
      getTask()
      break
    case 'end': // 结束任务
      localStorage.setItem('taskStatus', '0')
      window.location.reload()
      break
    case 'reload': // 保持登陆
      reloadTable()
      break
    case 'logout': // 退出代运营状态
      childLogout()
      break
    case 'selected':
      const selectedInfo = request.selectedInfo;
      localStorage.setItem('selectedProvince', selectedInfo.province);
      localStorage.setItem('selectedCity', selectedInfo.city);
      createNotification(`已选择省份：${selectedInfo.province}，城市：${selectedInfo.city}`);
      break;
    default:
      break
  }
})

// 页面加载完成后执行监听
async function watchPage() {
  await waitForPageLoad()
  createNotification('页面加载成功。。。')

  // 任务执行状态
  const taskStatus = localStorage.getItem('taskStatus')

  //
  if (taskStatus !== '1') {
    createNotification('非任务状态，不执行操作')
    return
  }

  // 分页面进行操作
  createNotification('当前页面：', window.location.href)
  switch (window.location.href) {
    case PAGE.creatorHomePage: // 机构号首页-获取任务
      getTask()
      break
    case PAGE.childCreatorHomePage: // 子账号首页
      createNotification('进入子账号')
      // 重新设置缓存标志位
      localStorage.setItem('isResetCache', '0')
      // 进入子页面先清空历史缓存数据
      removeStorageKey()
      // 跳转到子账号页面的上传
      toChildUploadPage()
      break
    case PAGE.childHomePage: // 子账号上传页面
      window.location.href = PAGE.childUploadPage
      break
    case PAGE.childUploadPage: // 子账号上传页面
      //  点击上传按钮
      uploadVideoFn()
      break

    case PAGE.childPublishPage: // 子账号发布页面
      // 点击发布按钮
      publishVideo()
      break

    case PAGE.childContentPage: // 子账号内容管理页面
      // 退出代运营状态
      childLogout()
      break

    default: // 其他页面
      break
  }
}
// 页面加载完成后执行监听
watchPage()

// 1. 同步账号 开始

// 获取所有账号列表数据
async function getAllAccount() {
  try {
    // 获取最大页码
    const maxPage = await getMaxPage()
    createNotification(`maxPage最大${maxPage}页`)
    // 获取表格的tr
    const rows = await waitForElement('.douyin-creator-pc-table-tbody tr', { isAll: true })
    // 遍历所有的tr元素
    rows.forEach((row, col) => {
      // 创建一个空对象来保存每行的数据
      const rowData = {}

      // 获取当前行的所有td元素
      const cells = row.querySelectorAll('td')

      // 获取每个td中的数据，并存储到rowData对象中
      rowData.avatar = cells[0].querySelector('img').src
      rowData.name = cells[0].querySelector('p').textContent.trim()
      rowData.dyAccountNo = cells[1].textContent.trim()
      rowData.date = cells[2].textContent.trim()
      rowData.actions = Array.from(cells[4].querySelectorAll('span'))
      rowData.sort = col

      // 将rowData对象添加到accountList数组中
      accountList.push(rowData)
    })
    const showAccountList = accountList.map((item) => item.name)
    createNotification(showAccountList, 'accountList')
    // 如果数据超过5条，尝试获取下一页数据
    if (maxPage > 1) {
      if (currentPage < maxPage) {
        createNotification('已获取子账号：' + accountList.length)
        await nextPage()
        return getAllAccount()
      } else {
        createNotification('所有页面的数据已获取完毕，准备同步')
        syncAccount()
      }
    } else {
      createNotification('子账号数量不足5个，准备同步')
      // 如果没有5个以上的子账号，直接同步
      syncAccount()
    }
  } catch (error) {
    $handleError('getTableAll获取账号列表数据失败：' + JSON.stringify(error))
  }
}

// 获取机构号
async function getMainAccount() {
  return new Promise(async (resolve, reject) => {
    try {
      const accountElement = await waitForElement('#sub-app p', { isAll: true })
      createNotification(accountElement, 'accountElement')
      const mainAccountId = accountElement[0].textContent
      resolve(mainAccountId)
    } catch (error) {
      $handleError('getMainAccountId获取机构号失败：' + JSON.stringify(error))
      reject(error)
    }
  })
}
// 同步账号信息
async function syncAccount() {
  const mainAccountId = await getMainAccount()
  // 去重
  const params = [...new Set(accountList)].map((item) => {
    return {
      mainAccountId,
      ...item
    }
  })
  try {
    // 调用接口传递给后台
    await $Request(API.syncAccountApi, {
      params
    })
    localStorage.setItem('accountList', JSON.stringify(params))
    createNotification(`同步账号接口请求结束，本次同步账号：${params.length}个`)
  } catch (error) {
    $handleError(error)
  }
}

// 1. 同步账号 结束

// 2. 开始任务 开始

// 获取缓存的task任务
function getCacheTask() {
  const task = parseJSON(localStorage.getItem('task'), {})
  return task?.id ? task : {}
}

// 获取要开始的任务
async function getTask() {
  // 获取存储的省份和城市
  /* const selectedInfo = localStorage.getItem('selectedInfo');
  const task = localStorage.getItem('task');

  console.log('selectedInfo:', selectedInfo);
  console.log('task:', task); */
  const selectedCity = localStorage.getItem('selectedCity');
  const selectedProvince = localStorage.getItem('selectedProvince');
  console.log('selectedCity:', selectedCity);
  console.log('selectedProvince:', selectedProvince);
  return;
  try {
    const mainAccountId = await getMainAccount()

    if (!mainAccountId || mainAccountId === null || mainAccountId === 'null') {
      createNotification(`${mainAccountId}：机构号错误，请先重新同步账号`)
      return
    }

    createNotification(`${mainAccountId}：准备获取要开始的任务`)

    const res = await $Request(`${API.getTaskApi}?mainAccountId=${mainAccountId}`, {})

    if (!res) {
      localStorage.setItem('taskStatus', '0')
      createNotification('没有新的任务')
      return
    }

    localStorage.setItem('task', JSON.stringify(res))

    // 进入子账号页面
    await getChildPage()
  } catch (error) {
    localStorage.setItem('taskStatus', '0')
    $handleError(`开始任务失败：${JSON.stringify(error)}`)
  }
}

// 点击管理跳转子账号页面
async function getChildPage() {
  try {
    // 进入成员管理tab
    await getContentTab('account')

    // 获取任务数据
    const task = getCacheTask()

    // 获取缓存的子账号列表
    const dataLists = parseJSON(localStorage.getItem('accountList'), [])

    // 找到子账号的索引
    const childIndex = dataLists.findIndex((item) => item.dyAccountNo === task.dyUserId)

    createNotification(`子账号索引: ${childIndex}`, 'childIndex', task.dyUserId)

    // 判断childIndex是否存在
    if (childIndex === -1) {
      $handleError('子账号没找到')
      return
    }

    // 计算页码
    const itemsPerPage = 5 // 每页显示的项目数
    const pageIndex = Math.ceil((childIndex + 1) / itemsPerPage)

    // 进入对应页码
    if (pageIndex > 1) {
      await goToPage(pageIndex)
    }

    // 获取当前页面的table
    await getChildAndClick()
  } catch (error) {
    $handleError(`点击跳转子账号页面中出现错误: ${JSON.stringify(error)}`)
  }
}
// 找到子账号并点击跳转
async function getChildAndClick() {
  try {
    currentAccountList.length = 0

    const task = getCacheTask()
    // 获取表格的tr
    const rows = await waitForElement('.douyin-creator-pc-table-tbody tr', { isAll: true })
    // 遍历所有的tr元素
    rows.forEach((row, col) => {
      // 创建一个空对象来保存每行的数据
      const rowData = {}

      // 获取当前行的所有td元素
      const cells = row.querySelectorAll('td')

      // 获取每个td中的数据，并存储到rowData对象中
      rowData.avatar = cells[0].querySelector('img').src
      rowData.name = cells[0].querySelector('p').textContent.trim()
      rowData.dyAccountNo = cells[1].textContent.trim()
      rowData.date = cells[2].textContent.trim()
      rowData.actions = Array.from(cells[4].querySelectorAll('span'))
      rowData.sort = col

      // 将rowData对象添加到dataList数组中
      currentAccountList.push(rowData)
    })

    const showAccountList = currentAccountList.map((item) => item.name)
    createNotification(showAccountList, '当前子账号列表')

    // 获取accountList中id为ID的元素
    const childAccount = currentAccountList.find((item) => item.dyAccountNo === task.dyUserId)
    createNotification(childAccount, '子账号')
    if (childAccount) {
      // 点击子账号的操作按钮
      createNotification('准备跳转子账号页面')
      await simulateClick(childAccount.actions[0])
    } else {
      localStorage.setItem('taskStatus', '0')
      $handleError('未找到子账号，请检查并重新同步账号')
      reloadPage()
    }
  } catch (error) {
    $handleError('getTable获取子账号具体位置失败：' + JSON.stringify(error))
  }
}

// 获取内容管理tab
async function getContentTab(tab) {
  const element = await waitForElement('div[role="tablist"]', { isAll: true })
  createNotification(element, 'element-getContentTab')
  const tabs = element[0].querySelectorAll('div[role="tab"]', { isAll: true })
  // 成员管理
  const accountTab = tabs[0]
  createNotification(accountTab, 'accountTab')
  // 数据统计tab
  const dataTab = tabs[1]
  createNotification(dataTab, 'dataTab')
  // 内容管理tab
  const contentTab = tabs[2]
  createNotification(contentTab, 'contentTab')
  let tabToClick = null
  switch (tab) {
    case 'account':
      // 点击成员管理
      if (accountTab) {
        tabToClick = accountTab
      }
      break
    case 'data':
      // 点击数据统计
      if (dataTab) {
        tabToClick = dataTab
      }
      break
    case 'content':
      // 点击内容管理
      if (contentTab) {
        tabToClick = contentTab
      }
      break

    default:
      break
  }

  tabToClick && (await simulateClick(tabToClick, 0))
}

// 获取子页面上导航栏
async function toChildUploadPage() {
  try {
    // 找到navList中的所有li元素
    const navListItems = await waitForElement('.semi-navigation-list li', { isAll: true })
    if (navListItems && navListItems.length) {
      await simulateClick(navListItems[1])
      createNotification('子页面上导航栏 clicked')
    } else {
      $handleError('未找到子页面上导航栏')
      reloadPage()
    }
  } catch (error) {
    $handleError(error)
    reloadPage()
  }
}

// 通过接口获取文件路径
async function uploadVideoFn() {
  try {
    createNotification('准备上传视频')

    // 获取任务数据
    const task = getCacheTask()
    const { filePath, videoName } = task

    // 将autoFillFormCount初始化并放入缓存
    localStorage.setItem('cacheAutoFillFormCount', 0)
    const file = await urlToFile(filePath, videoName)
    // 获取上传按钮，并将file上传
    const inputElement = await waitForElement('input[type="file"][name="upload-btn"]', {
      isAll: true
    })
    if (inputElement[0]) {
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(file)
      inputElement[0].files = dataTransfer.files

      // 触发 change 事件以确保上传组件检测到文件
      const event = new Event('change', { bubbles: true })
      inputElement[0].dispatchEvent(event)
      createNotification('文件上传成功')
      // 检查视频是否已经加载好
      checkUploadVideo()
    } else {
      $handleError('未找到上传按钮')
    }
  } catch (error) {
    $handleError('未找到上传按钮' + JSON.stringify(error))
  }
}

// 上传后检查是否加载成功
async function checkUploadVideo() {
  createNotification('检查是否加载成功')
  try {
    const videoElement = await waitForElement('video')
    if (videoElement) {
      // 检查视频是否已经加载好
      if (videoElement.readyState >= 3) {
        createNotification('videoElement already loaded')
        reloadPage()
      } else {
        createNotification('videoElement not yet loaded, adding event listener')
        videoElement.addEventListener('loadeddata', async () => {
          createNotification('videoElement loadeddata')
          reloadPage()
        })
      }
    } else {
      // 如果视频元素不存在，输出错误信息,并继续调用checkUploadVideo
      $handleError('未找到视频元素')
      await delay(DELAY.DOM_DELAY)
      checkUploadVideo()
    }
  } catch (error) {
    $handleError(error)
    taskFailed('上传后检查是否加载成功中出现错误', error)
  }
}

// 视频加载完毕后写入缓存准备发布
async function publishVideo(_videoElement) {
  try {
    const task = getCacheTask()
    // 检查是否需要重新写入缓存
    const cacheFlag = localStorage.getItem('isResetCache')

    if (cacheFlag !== '1') {
      const flag = await autoFillForm()
      if (flag) {
        reloadPage()
      } else {
        $handleError('表单自动填写失败')
      }
    } else {
      // 已经填写过表单，进行发布操作
      createNotification('表单已自动填写，进行发布操作')

      // 如果有封面，需要做封面操作
      if (task && task.task && task.task.coverPath) {
        await choseCoverImage()
      }
      // 发布方式选择
      await publishTimePickerSelect()

      // 点击发布按钮
      createNotification('点击发布按钮')
      const publishButtons = await waitForElement('button', { isAll: true })
      // 遍历按钮，查找内容为 "发布" 的按钮
      for (const button of publishButtons) {
        if (button.textContent.trim() === '发布') {
          await publishSuccess()
          await simulateClick(button)
          // 退出代运营状态
          window.location.href = PAGE.childContentPage
        }
      }
    }
  } catch (error) {
    $handleError('表单自动填写过程中出现错误' + JSON.stringify(error))
  }
}

// 自动填充表单，写入缓存后刷新一次页面，如果再次进入则不再填充
// 自动填充表单
async function autoFillForm() {
  createNotification('自动填充表单')

  return new Promise(async (resolve, reject) => {
    let flag = false
    // 获取任务数据
    const task = getCacheTask()
    // 缓存的自动填充表单次数
    let cacheAutoFillFormCount = localStorage.getItem('cacheAutoFillFormCount')
    try {
      // 如果 task.topicName 存在
      if (task.topicName) {
        // 使用正则表达式查找所有的 #
        const matches = task.topicName.match(/#/g) || []

        // 计算 # 的数量
        batchTopicCount = matches.length
        isBatchTopic = batchTopicCount > 1

        // 分割 topicName 并过滤掉空字符串
        topicNames = task.topicName.split('#').filter(Boolean)
      }

      // 获取缓存数据
      const cacheList = await getStorageKey()
      //
      if (cacheList && cacheList.length) {
        createNotification('获取缓存list', cacheList)
        cacheList.forEach((item) => {
          const cacheItem = localStorage.getItem(item)
          if (!cacheItem || cacheItem === 'null' || cacheItem === 'undefined') {
            return
          }

          // 获取缓存数据
          const { type, cache } = parseJSON(cacheItem, {})
          const oldTextExtra = cache.textResult.textExtra
          const oldText = cache.textResult.text

          // 重新赋值 cache 数据
          const newCacheData = {
            ...cache,
            itemTitle: task.videoName || '',
            textResult: {
              text: oldText
                ? oldText +
                (topicNames[cacheAutoFillFormCount]
                  ? '#' + topicNames[cacheAutoFillFormCount]
                  : '')
                : (task.remark || '') +
                (topicNames[cacheAutoFillFormCount]
                  ? '#' + topicNames[cacheAutoFillFormCount]
                  : ''),
              textExtra: [...(oldTextExtra || [])], // 深拷贝 oldTextExtra 数组
              activity: [],
              caption: ''
              // caption: task.topicName ? (task.remark || '') + task.topicName : task.remark || ''
            }
          }
          const newData = JSON.stringify({ type, cache: newCacheData })
          localStorage.setItem(item, newData)
        })
      } else {
        createNotification('没有找到缓存')
        $handleError('没有找到缓存')
        return
      }
      // 如果有话题，需要做话题操作
      if (topicNames && topicNames.length && topicNames[cacheAutoFillFormCount] !== undefined) {
        createNotification('话题操作---' + topicNames[cacheAutoFillFormCount])
        await topicOperation(topicNames[cacheAutoFillFormCount])
      }

      // 如果有poi地址，需要做poi操作
      if (task && task.task && task.task.poiAddressName) {
        await poiOperation(task.task.poiAddressName)
      }

      createNotification('表单自动填写成功')

      // 修改缓存的autoFillFormCount
      cacheAutoFillFormCount++
      // 如果autoFillCount不等于topicNames长度，继续填充，否则设置标志位，表明已经填写过表单
      createNotification(cacheAutoFillFormCount, 'cacheAutoFillFormCount')
      createNotification(topicNames.length, 'topicNames.length ')

      if (cacheAutoFillFormCount != topicNames.length && topicNames.length > 0) {
        localStorage.setItem('cacheAutoFillFormCount', cacheAutoFillFormCount)
        flag = true
      } else {
        localStorage.setItem('isResetCache', '1')
        flag = true
      }
      resolve(flag) // 返回成功标志
    } catch (error) {
      $handleError('autoFillForm 出现错误:' + JSON.stringify(error))
      reject(error) // 返回错误信息
    }
  })
}

// 话题操作
async function topicOperation(txt) {
  const element = await waitForElement('.mention-suggest-mount-dom span', { isAll: true })
  createNotification(element, 'element', txt)
  // 找到所有的span标签，如果是#则点击索引为0的span标签
  if (element && element.length) {
    const span = Array.from(element).find((item) => item.innerText === txt)
    createNotification(span, 'span')
    if (span) {
      // 找到span的父元素
      const parent = span.parentElement
      createNotification(parent, 'span---话题点击了')
      await simulateClick(parent)
    }
  } else {
    $handleError('没有找到----topicOperation')
  }
}

// POI地址操作
async function poiOperation(txt) {
  await delay(DELAY.PAGE_DELAY)
  const select = await waitForElement('#douyin_creator_pc_anchor_jump .semi-select-selection')
  createNotification(select, 'select')
  // 下拉选择点击
  await simulateClick(select)
  // 找到input
  const input = await waitForElement(
    '#douyin_creator_pc_anchor_jump .semi-select-selection input[type="text"]'
  )
  input.value = txt
  // 触发input的input事件
  input.dispatchEvent(new Event('input', { bubbles: true }))
  createNotification(input, 'input----dispatchEvent', txt)
  await delay(DELAY.DOM_DELAY)
  // 找到popover-content
  const popoverContent = await waitForElement(
    '.semi-popover .semi-popover-content .semi-select-option-list .semi-select-option',
    { isAll: true }
  )
  createNotification(popoverContent, 'popoverContent')
  if (popoverContent && popoverContent.length) {
    // 点击第一个

    await simulateClick(popoverContent[0])
    createNotification(popoverContent[0], 'poi点击了')
  } else {
    $handleError('没有找到----poiOperation')
  }
}

// 选择上传封面图片
async function choseCoverImage() {
  createNotification('封面操作')
  const element = await waitForElement('.content-upload-new svg', {
    isAll: true
  })
  createNotification(element, 'element----choseCoverImage')
  if (element && element.length) {
    createNotification('找到封面图片上传')
    await simulateClick(element[0].parentElement)
    await choseCoverImageTab() // 使用 await 确保点击完成后再执行
  } else {
    $handleError('未找到封面图片上传')
  }
}

// 上传封面图弹窗tab选择
async function choseCoverImageTab() {
  const element = await waitForElement('.semi-modal-body div', { isAll: true })
  if (element && element.length) {
    // textContent 为 '上传封面' 的元素
    const tab = Array.from(element).find((item) => item.textContent === '上传封面')

    createNotification('找到封面图片上传tab', tab)

    await simulateClick(tab) // 使用 await 确保点击完成后再执行

    // 上传封面图
    // 找到semi-upload中的input且type=file的元素
    const inputElement = await waitForElement('.semi-upload input[type="file"]', {
      isAll: true
    })
    createNotification(inputElement, 'inputElement---封面图上传的input')
    // 将url转换为file，然后上传
    const task = getCacheTask()
    const file = await urlToFile(task?.task?.coverPath)
    const dataTransfer = new DataTransfer()
    dataTransfer.items.add(file)
    inputElement[0].files = dataTransfer.files
    // 触发 change 事件以确保上传组件检测到文件
    const event = new Event('change', { bubbles: true })
    inputElement[0].dispatchEvent(event)
    createNotification('封面图 File uploaded successfully')

    // 找到canvas-container。检查元素下的子元素id为uploadCrop的canvas是否有值
    const uploadCropElement = await waitForElement('.canvas-container #uploadCrop')
    createNotification(uploadCropElement, 'uploadCropElement')
    // 判断是否有值
    if (uploadCropElement && uploadCropElement.toDataURL()) {
      createNotification('uploadCropElement.toDataURL()', uploadCropElement.toDataURL())
      // 点击确定按钮,有2个tab，一个是选取封面，一个是上传封面，需要倒序一下
      const confirmButton = await waitForElement('.semi-modal-body button', { isAll: true })
      createNotification(confirmButton, 'confirmButton')
      // 倒序找到文字为完成的按钮
      const confirm = Array.from(confirmButton)
        .reverse()
        .find((item) => item.textContent === '完成')
      createNotification(confirm, 'confirm')
      await simulateClick(confirm) // 使用 await 确保点击完成后再执行
    } else {
      $handleError('未找到uploadCropElement或者uploadCropElement.toDataURL()为空')
    }
  } else {
    $handleError('未找到上传封面图弹窗tab选择')
  }
}
// 发布成功后通知后台
async function publishSuccess() {
  try {
    // 获取任务数据
    const task = getCacheTask()
    await $Request(API.updateAutoPublishTaskApi, {
      params: {
        id: task.id
      }
    })

    createNotification('发出发布成功接口请求，准备退出代运营状态')
  } catch (error) {
    $handleError('发布成功后通知后台出现错误' + JSON.stringify(error))
  }
}

// 2. 开始任务 结束

// 4. 保持登陆 开始

// 保持登陆使用---重新加载table
async function reloadTable() {
  try {
    // 获取最大页码
    await getMaxPage()
    // 如果不是最后一页，轮流跳转到最后一页
    while (currentPage < maxPage) {
      nextPage()
      await delay(DELAY.PAGE_DELAY)
    }
    // 如果是最后一页，再次获取最大页码
    await getMaxPage()
    // 如果不是第一页，轮流跳转到第一页
    while (currentPage > 1) {
      prevPage()
      await delay(DELAY.PAGE_DELAY)
    }
    // 如果是第一页，再次获取最大页码
    await getMaxPage()
    // 10秒后重新获取表格数据
    await delay(DELAY.PAGE_DELAY)
    reloadTable()
  } catch (error) {
    $handleError(error)
  }
}

// 4. 保持登陆 结束

// 退出代运营状态-开始
// 退出登录
async function childLogout() {
  try {
    await delay(DELAY.DOM_DELAY) // 等待页面加载

    const logoutButton = await waitForElement('.semi-navigation-footer .semi-avatar')
    // 获取按钮的具体位置
    const logoutButtonRect = logoutButton.getBoundingClientRect()
    simulateMouseMove(
      logoutButtonRect.x + logoutButtonRect.width / 2,
      logoutButtonRect.y + logoutButtonRect.height / 2
    )
    createNotification('logoutButton clicked')

    await delay(DELAY.DOM_DELAY) // 等待下拉菜单出现
    const logout = await waitForElement('.semi-portal .logout')
    createNotification(logout)

    if (logout) {
      await simulateClick(logout)
      createNotification('logout clicked')
    } else {
      // 重新进入子账号页面
      window.location.href = PAGE.childContentPage
    }
  } catch (error) {
    $handleError('childLogout error' + JSON.stringify(error))
  }
}

// 退出代运营状态-结束
