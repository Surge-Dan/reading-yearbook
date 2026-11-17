# 兼容测试源码夹具

两个`.py.txt`文件来自本仓库历史版本，仅用于生成旧缓存并验证迁移，不参与Skill安装或新任务运行：

- ebook-pipeline-dfbea09.py.txt：提交dfbea095e843d296a9e212a8172a11dd76a65da5的scripts/ebook_pipeline.py，测试五类抽取缓存向联合抽取迁移。
- ebook-pipeline-a9c06c6.py.txt：提交a9c06c6的同名文件，测试上下文理解规则变化后的阶段缓存失效。

这样在浅克隆、源码压缩包和CI中也能复现，不再通过git show读取本机历史。来源仓库为https://github.com/Surge-Dan/reading-yearbook。第三方方法与许可仍由Skill的third_party/cangjie固定清单维护；测试使用受控模型替身，不调用真实模型或账号。
