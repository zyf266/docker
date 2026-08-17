import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

/** 可选：自定义女性 GLB；未配置则用本地程序化女半身（不依赖外网模型） */
const CUSTOM_MODEL =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_XIAOMO_MODEL_URL) || ''

function buildProceduralXiaomo() {
  const root = new THREE.Group()

  // 头发后层
  const hairBack = new THREE.Mesh(
    new THREE.SphereGeometry(0.42, 24, 18, 0, Math.PI * 2, 0, Math.PI * 0.72),
    new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.85 })
  )
  hairBack.position.set(0, 1.62, -0.04)
  hairBack.scale.set(1.05, 1.1, 1.05)
  root.add(hairBack)

  // 刘海
  const bang = new THREE.Mesh(
    new THREE.SphereGeometry(0.38, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.38),
    new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.8 })
  )
  bang.position.set(0, 1.78, 0.12)
  bang.rotation.x = -0.35
  root.add(bang)

  // 侧发
  const sideMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.85 })
  ;[-1, 1].forEach((side) => {
    const sideHair = new THREE.Mesh(new THREE.CapsuleGeometry(0.09, 0.35, 4, 8), sideMat)
    sideHair.position.set(side * 0.32, 1.45, 0.02)
    sideHair.rotation.z = side * 0.15
    root.add(sideHair)
  })

  // 脸
  const face = new THREE.Mesh(
    new THREE.SphereGeometry(0.34, 28, 22),
    new THREE.MeshStandardMaterial({ color: 0xfbbf24, roughness: 0.55, metalness: 0.05 })
  )
  face.position.set(0, 1.55, 0.06)
  face.scale.set(1, 1.08, 0.92)
  root.add(face)

  // 眼睛
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4 })
  ;[-1, 1].forEach((side) => {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.045, 12, 10), eyeMat)
    eye.position.set(side * 0.11, 1.58, 0.36)
    root.add(eye)
    const highlight = new THREE.Mesh(
      new THREE.SphereGeometry(0.015, 8, 8),
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.2 })
    )
    highlight.position.set(side * 0.1, 1.59, 0.39)
    root.add(highlight)
  })

  // 嘴（说话时拉高）
  const mouth = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.05, 0.02, 4, 8),
    new THREE.MeshStandardMaterial({ color: 0xb45309, roughness: 0.6 })
  )
  mouth.position.set(0, 1.4, 0.36)
  mouth.rotation.z = Math.PI / 2
  mouth.name = 'xiaomoMouth'
  root.add(mouth)

  // 肩/衣领
  const torso = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.28, 0.35, 6, 12),
    new THREE.MeshStandardMaterial({ color: 0x0f766e, roughness: 0.55 })
  )
  torso.position.set(0, 0.85, 0)
  root.add(torso)

  const collar = new THREE.Mesh(
    new THREE.TorusGeometry(0.16, 0.035, 8, 20, Math.PI),
    new THREE.MeshStandardMaterial({ color: 0x5eead4, roughness: 0.5 })
  )
  collar.position.set(0, 1.12, 0.12)
  collar.rotation.x = Math.PI / 2
  root.add(collar)

  // 耳坠点缀
  ;[-1, 1].forEach((side) => {
    const earring = new THREE.Mesh(
      new THREE.SphereGeometry(0.03, 8, 8),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.6, roughness: 0.3 })
    )
    earring.position.set(side * 0.34, 1.42, 0.05)
    root.add(earring)
  })

  return { root, mouth }
}

/**
 * 半身 3D + 音量口型。默认程序化女半身；可配 VITE_XIAOMO_MODEL_URL。
 */
const XiaomoAvatar3D = ({ speaking, audioEl, className = '', onFail, onReady }) => {
  const mountRef = useRef(null)
  const mouthOpenRef = useRef(0)
  const analyserRef = useRef(null)
  const rafRef = useRef(0)
  const speakingRef = useRef(speaking)
  const onFailRef = useRef(onFail)
  const onReadyRef = useRef(onReady)
  const [failed, setFailed] = useState(false)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    speakingRef.current = speaking
  }, [speaking])

  useEffect(() => {
    onFailRef.current = onFail
  }, [onFail])

  useEffect(() => {
    onReadyRef.current = onReady
  }, [onReady])

  useEffect(() => {
    const el = mountRef.current
    if (!el) return undefined

    let disposed = false
    const w = el.clientWidth || 88
    const h = el.clientHeight || 104

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(32, w / h, 0.05, 50)
    camera.position.set(0, 1.45, 2.05)
    camera.lookAt(0, 1.35, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.setSize(w, h)
    renderer.setClearColor(0x000000, 0)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    el.appendChild(renderer.domElement)

    scene.add(new THREE.HemisphereLight(0xfff7ed, 0x334155, 1.2))
    const key = new THREE.DirectionalLight(0xffffff, 1.05)
    key.position.set(0.8, 2.4, 1.6)
    scene.add(key)

    /** @type {THREE.Object3D | null} */
    let mouthObj = null
    /** @type {{ mesh: THREE.Mesh, index: number }[]} */
    let morphMouths = []
    const clock = new THREE.Clock()

    const finishReady = () => {
      if (disposed) return
      setReady(true)
      onReadyRef.current?.()
    }

    const fail = () => {
      if (disposed) return
      setFailed(true)
      onFailRef.current?.()
    }

    const mountProcedural = () => {
      const { root, mouth } = buildProceduralXiaomo()
      mouthObj = mouth
      scene.add(root)
      finishReady()
    }

    if (CUSTOM_MODEL) {
      const loader = new GLTFLoader()
      loader.load(
        CUSTOM_MODEL,
        (gltf) => {
          if (disposed) return
          const root = gltf.scene
          root.traverse((obj) => {
            if (!obj.isMesh) return
            obj.frustumCulled = false
            const dict = obj.morphTargetDictionary
            if (!dict || !obj.morphTargetInfluences) return
            for (const keyName of ['mouthOpen', 'jawOpen', 'mouthSmile']) {
              if (keyName in dict) morphMouths.push({ mesh: obj, index: dict[keyName] })
            }
          })
          root.position.set(0, -0.9, 0)
          root.scale.setScalar(1.1)
          camera.position.set(0, 1.55, 1.1)
          camera.lookAt(0, 1.5, 0)
          scene.add(root)
          finishReady()
        },
        undefined,
        () => {
          // 自定义模型失败 → 程序化女半身
          mountProcedural()
        }
      )
    } else {
      mountProcedural()
    }

    const tick = () => {
      if (disposed) return
      rafRef.current = requestAnimationFrame(tick)
      clock.getDelta()

      const isSpeaking = speakingRef.current
      let target = isSpeaking ? 0.4 : 0
      const analyser = analyserRef.current
      if (analyser && isSpeaking) {
        const data = new Uint8Array(analyser.frequencyBinCount)
        analyser.getByteFrequencyData(data)
        let sum = 0
        for (let i = 0; i < data.length; i += 1) sum += data[i]
        const avg = sum / (data.length || 1) / 255
        target = Math.min(1, 0.2 + avg * 2.6)
      }
      mouthOpenRef.current += (target - mouthOpenRef.current) * 0.4
      const v = mouthOpenRef.current

      if (mouthObj) {
        mouthObj.scale.set(1, 1 + v * 2.2, 1 + v * 1.4)
      }
      for (const t of morphMouths) {
        if (t.mesh.morphTargetInfluences) t.mesh.morphTargetInfluences[t.index] = v
      }

      renderer.render(scene, camera)
    }
    tick()

    const onResize = () => {
      if (!mountRef.current) return
      const nw = mountRef.current.clientWidth || 88
      const nh = mountRef.current.clientHeight || 104
      camera.aspect = nw / nh
      camera.updateProjectionMatrix()
      renderer.setSize(nw, nh)
    }
    window.addEventListener('resize', onResize)

    return () => {
      disposed = true
      cancelAnimationFrame(rafRef.current)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      if (renderer.domElement.parentNode === el) el.removeChild(renderer.domElement)
    }
  }, [])

  useEffect(() => {
    if (!audioEl) {
      analyserRef.current = null
      return undefined
    }
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return undefined
      const ctx = new Ctx()
      const src = ctx.createMediaElementSource(audioEl)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      src.connect(analyser)
      analyser.connect(ctx.destination)
      analyserRef.current = analyser
      const resume = () => {
        if (ctx.state === 'suspended') void ctx.resume()
      }
      audioEl.addEventListener('play', resume)
      return () => {
        audioEl.removeEventListener('play', resume)
        try {
          src.disconnect()
          analyser.disconnect()
          void ctx.close()
        } catch {
          /* ignore */
        }
        analyserRef.current = null
      }
    } catch {
      analyserRef.current = null
      return undefined
    }
  }, [audioEl])

  if (failed) return null

  return (
    <div
      ref={mountRef}
      className={`xiaomo-3d${ready ? ' ready' : ''}${className ? ` ${className}` : ''}`}
      aria-hidden
    />
  )
}

export default XiaomoAvatar3D
