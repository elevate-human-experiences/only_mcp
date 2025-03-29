import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface EntityRecord {
  id: string;
  data: any;
}

interface EntitiesPageProps {
  token: string;
}

export function EntitiesPage({ token }: EntitiesPageProps) {
  const [types, setTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState("");
  const [entities, setEntities] = useState<EntityRecord[]>([]);
  const [newEntityData, setNewEntityData] = useState("{}");

  // Fetch available schema types
  useEffect(() => {
    fetch("/api/schema", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        // Suppose the server returns { schemas: [{type: 'Book'}, {type: 'User'}] }
        if (data.schemas && Array.isArray(data.schemas)) {
          const typeList = data.schemas.map((s: any) => s.type);
          setTypes(typeList);
          if (typeList.length > 0) {
            setSelectedType(typeList[0]);
          }
        }
      })
      .catch((err) => console.error("Error fetching schemas", err));
  }, [token]);

  // Fetch entities of selectedType
  useEffect(() => {
    if (!selectedType) return;
    fetch(`/api/entity?type=${encodeURIComponent(selectedType)}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.entities && Array.isArray(data.entities)) {
          setEntities(data.entities);
        } else {
          setEntities([]);
        }
      })
      .catch((err) => console.error("Error fetching entities", err));
  }, [selectedType, token]);

  const handleCreate = async () => {
    try {
      const parsedData = JSON.parse(newEntityData);
      const res = await fetch("/api/entity", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          type: selectedType,
          data: parsedData,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        alert(`Create failed: ${errData.description || res.statusText}`);
        return;
      }
      const result = await res.json();
      alert(`Entity created with ID: ${result.id}`);
      setNewEntityData("{}");
      // Refetch entities
      fetch(`/api/entity?type=${encodeURIComponent(selectedType)}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((d) => setEntities(d.entities || []));
    } catch (e: any) {
      alert(`Invalid JSON or other error: ${e.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this entity?")) return;
    const res = await fetch(
      `/api/entity?type=${encodeURIComponent(selectedType)}&id=${id}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      alert(`Delete failed: ${errData.description || res.statusText}`);
      return;
    }
    // Update local list
    setEntities(entities.filter((e) => e.id !== id));
  };

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Entities</h1>

      <div className="mb-4">
        <label className="mr-2 font-medium">Select Entity Type:</label>
        <select
          className="border p-1 rounded"
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
        >
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {entities.length === 0 && (
        <p className="mb-4">No entities found for type "{selectedType}".</p>
      )}

      <ul className="space-y-2 mb-6">
        {entities.map((entity) => (
          <li
            key={entity.id}
            className="p-2 border rounded flex justify-between items-center"
          >
            <div className="text-sm">
              <span className="font-bold">ID:</span> {entity.id}
              <br />
              <span className="font-bold">Data:</span>{" "}
              <pre className="inline bg-gray-100 p-1">
                {JSON.stringify(entity.data)}
              </pre>
            </div>
            <Button
              variant="destructive"
              onClick={() => handleDelete(entity.id)}
            >
              Delete
            </Button>
          </li>
        ))}
      </ul>

      <div className="border p-4 rounded">
        <h2 className="font-bold mb-2">Create New Entity: {selectedType}</h2>
        <Textarea
          className="w-full h-32"
          value={newEntityData}
          onChange={(e) => setNewEntityData(e.target.value)}
        />
        <Button className="mt-2" onClick={handleCreate}>
          Create
        </Button>
      </div>
    </div>
  );
}
