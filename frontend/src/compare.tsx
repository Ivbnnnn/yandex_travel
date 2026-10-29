import { createContext, useContext, useState, type ReactNode } from 'react'

interface CompareValue { ids: string[]; toggle: (id: string) => boolean; clear: () => void }
const Ctx = createContext<CompareValue>(null!)
export const useCompare = () => useContext(Ctx)

// Для сравнения выбирается от 2 до 3 отелей; хранится в sessionStorage
export function CompareProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<string[]>(() => {
    try {
      return JSON.parse(sessionStorage.getItem('compare') ?? '[]')
    } catch {
      return []
    }
  })
  const save = (next: string[]) => {
    setIds(next)
    sessionStorage.setItem('compare', JSON.stringify(next))
  }
  // false — если лимит в 3 отеля уже достигнут
  const toggle = (id: string) => {
    if (ids.includes(id)) {
      save(ids.filter((x) => x !== id))
      return true
    }
    if (ids.length >= 3) return false
    save([...ids, id])
    return true
  }
  return <Ctx.Provider value={{ ids, toggle, clear: () => save([]) }}>{children}</Ctx.Provider>
}
